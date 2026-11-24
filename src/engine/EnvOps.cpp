//    sapf-sc - sapf interpreter for SuperCollider
//
//    This program is free software: you can redistribute it and/or modify
//    it under the terms of the GNU General Public License as published by
//    the Free Software Foundation, either version 3 of the License, or
//    (at your option) any later version.

// The env namespace: SC's Env constructors, with SC's defaults and array formats
// (SCClassLibrary/Common/Audio/Env.sc).

#include "Env.hpp"
#include "Def.hpp"
#include "Graph.hpp"
#include "Namespace.hpp"
#include <cstring>

namespace {

// SC's Env.shapeNames; a real or a UGen is curvature, shape 5.
int shapeNumber(Arg curve, const char* msg)
{
	if (!curve.isString()) return 5;
	static const struct { const char* name; int shape; } names[] = {
		{"step", 0}, {"lin", 1}, {"linear", 1}, {"exp", 2}, {"exponential", 2}, {"sin", 3}, {"sine", 3},
		{"wel", 4}, {"welch", 4}, {"sqr", 6}, {"squared", 6}, {"cub", 7}, {"cubed", 7}, {"hold", 8}};
	const char* s = ((String*)curve.o())->s;
	for (auto& n : names)
		if (!strcmp(s, n.name)) return n.shape;
	post("%s : no envelope shape named '%s\n", msg, s);
	throw errOutOfRange;
}

V curveValue(Arg curve) { return curve.isString() ? V(0.) : curve; }

} // namespace

void Env::print(Thread& th, std::string& out, int depth)
{
	auto list = [&](std::vector<V> const& vs) {
		out += "[";
		for (size_t i = 0; i < vs.size(); ++i) {
			if (i) out += " ";
			if (vs[i].isString()) out += "'";
			vs[i].print(th, out, depth + 1);
		}
		out += "]";
	};
	out += "Env(";
	list(levels);
	out += " ";
	list(times);
	out += " ";
	list(curves);
	out += ")";
}

std::vector<V> Env::envGenArray(const char* msg) const
{
	std::vector<V> a = {levels[0], (double)times.size(), releaseNode, loopNode};
	for (size_t i = 0; i < times.size(); ++i) {
		Arg c = curves[i % curves.size()];
		a.insert(a.end(), {levels[i + 1], times[i], (double)shapeNumber(c, msg), curveValue(c)});
	}
	return a;
}

std::vector<V> Env::interpolationArray(Thread& th, const char* msg) const
{
	V total = times[0];
	for (size_t i = 1; i < times.size(); ++i) total = graphBinary(th, opAdd, total, times[i]);
	std::vector<V> a = {offset, levels[0], (double)times.size(), total};
	for (size_t i = 0; i < times.size(); ++i) {
		Arg c = curves[i % curves.size()];
		a.insert(a.end(), {times[i], (double)shapeNumber(c, msg), curveValue(c), levels[i + 1]});
	}
	return a;
}

extern BinaryOp* gBinaryOpPtr_plus;
extern BinaryOp* gBinaryOpPtr_mul;

namespace {

// A level, time or curvature: a real, a UGen, or a list of them for several channels.
V popPoint(Thread& th, const char* msg)
{
	V v = th.pop();
	if (v.isRef() || v.isZRef()) v = v.deref();
	if (v.isList()) {
		if (!((List*)v.o())->isFinite()) indefiniteOp(msg, "");
		return V(((List*)v.o())->pack(th));
	}
	if (!v.isReal() && !isSig(v)) wrongType(msg, "Real, UGen or list", v);
	return v;
}

V popCurve(Thread& th, const char* msg)
{
	V v = th.pop();
	if (v.isString()) {
		shapeNumber(v, msg);
		return v;
	}
	th.push(v);
	return popPoint(th, msg);
}

std::vector<V> items(Thread& th, Arg v)
{
	if (!v.isList()) return {v};
	P<List> list = ((List*)v.o())->pack(th);
	std::vector<V> out;
	for (int64_t i = 0; i < list->mArray->size(); ++i) out.push_back(list->mArray->at(i));
	return out;
}

void pushEnv(Thread& th, std::vector<V> levels, std::vector<V> times, std::vector<V> curves, double releaseNode = -99.)
{
	P<Env> env = new Env();
	env->levels = std::move(levels);
	env->times = std::move(times);
	env->curves = std::move(curves);
	env->releaseNode = releaseNode;
	th.push(V(env));
}

// a op b, packed; a real identity operand returns the other, as sclang's BinaryOpUGen does
V arith(Thread& th, BinaryOp* op, double identity, V a, Arg b)
{
	if (b.isReal() && b.f == identity) return a;
	if (a.isReal() && a.f == identity) return b;
	V v = a.binaryOp(th, op, b);
	return v.isList() ? V(((List*)v.o())->pack(th)) : v;
}

// One or more curves, wrapped per segment.
std::vector<V> popCurves(Thread& th, const char* msg)
{
	std::vector<V> cs = items(th, popCurve(th, msg));
	if (cs.empty()) {
		post("%s : needs one or more curves\n", msg);
		throw errOutOfRange;
	}
	for (Arg c : cs)
		if (c.isString()) shapeNumber(c, msg);
	return cs;
}

void perc_(Thread& th, Prim* prim)
{
	std::vector<V> curve = popCurves(th, "env.perc : curve");
	V level = popPoint(th, "env.perc : level");
	V rel = popPoint(th, "env.perc : releaseTime");
	V atk = popPoint(th, "env.perc : attackTime");
	pushEnv(th, {0., level, 0.}, {atk, rel}, curve);
}

void adsr_(Thread& th, Prim* prim)
{
	V bias = popPoint(th, "env.adsr : bias");
	std::vector<V> curve = popCurves(th, "env.adsr : curve");
	V peak = popPoint(th, "env.adsr : peakLevel");
	V rel = popPoint(th, "env.adsr : releaseTime");
	V sus = popPoint(th, "env.adsr : sustainLevel");
	V dec = popPoint(th, "env.adsr : decayTime");
	V atk = popPoint(th, "env.adsr : attackTime");
	std::vector<V> levels = {0., peak, arith(th, gBinaryOpPtr_mul, 1., peak, sus), 0.};
	for (V& l : levels) l = arith(th, gBinaryOpPtr_plus, 0., l, bias);
	pushEnv(th, levels, {atk, dec, rel}, curve, 2.);
}

void asr_(Thread& th, Prim* prim)
{
	std::vector<V> curve = popCurves(th, "env.asr : curve");
	V rel = popPoint(th, "env.asr : releaseTime");
	V sus = popPoint(th, "env.asr : sustainLevel");
	V atk = popPoint(th, "env.asr : attackTime");
	pushEnv(th, {0., sus, 0.}, {atk, rel}, curve, 1.);
}

void linen_(Thread& th, Prim* prim)
{
	std::vector<V> curve = popCurves(th, "env.linen : curve");
	V level = popPoint(th, "env.linen : level");
	V rel = popPoint(th, "env.linen : releaseTime");
	V sus = popPoint(th, "env.linen : sustainTime");
	V atk = popPoint(th, "env.linen : attackTime");
	pushEnv(th, {0., level, level, 0.}, {atk, sus, rel}, curve);
}

// SC's Env.new: times wrap to one per segment; curves wrap per segment when read.
void new_(Thread& th, Prim* prim)
{
	V curves = popCurve(th, "env.new : curves");
	V times = popPoint(th, "env.new : times");
	V levels = popPoint(th, "env.new : levels");
	std::vector<V> ls = items(th, levels), ts = items(th, times), cs = items(th, curves);
	if (ls.size() < 2 || ts.empty() || cs.empty()) {
		post("env.new : needs 2 or more levels, and times and curves\n");
		throw errOutOfRange;
	}
	for (Arg c : cs)
		if (c.isString()) shapeNumber(c, "env.new : curves");
	std::vector<V> segs;
	for (size_t i = 0; i + 1 < ls.size(); ++i) segs.push_back(ts[i % ts.size()]);
	pushEnv(th, ls, segs, cs);
}

struct EnvParam { const char* name; V def; };

// An env constructor in SC's argument order. It takes the leading shape arguments from the stack
// and the rest, such as curve, at SC's defaults; a Form in their place names any of them.
class EnvPrim : public Prim
{
	std::vector<EnvParam> mParams;
	std::string mWord;
public:
	EnvPrim(const char* word, PrimFun fun, int positional, std::vector<EnvParam> params, const char* help)
		: Prim(fun, 0., (uint16_t)positional, 1, word, help), mParams(std::move(params)),
		  mWord(std::string("env.") + word) {}

	virtual void apply(Thread& th) override
	{
		if (th.stackDepth() >= 1 && th.top().isForm()) {
			V form = th.pop();
			for (auto& [key, v] : formPairs(th, (Form*)form.o())) {
				bool known = false;
				for (auto& p : mParams) known |= key == p.name;
				if (!known) {
					post("%s : no argument named %s\n", mWord.c_str(), key.c_str());
					throw errNotFound;
				}
			}
			for (auto& p : mParams) {
				V v;
				th.push(((Form*)form.o())->get(th, V(getsym(p.name)), v) ? v : p.def);
			}
		} else {
			if (th.stackDepth() < mTakes) throw errStackUnderflow;
			for (size_t i = mTakes; i < mParams.size(); ++i) th.push(mParams[i].def);
		}
		apply_n(th, mParams.size());
	}
};

void addEnvPrim(Namespace* ns, const char* word, PrimFun fun, int positional, std::vector<EnvParam> params,
	const char* help)
{
	ns->mWords[word] = V(new EnvPrim(word, fun, positional, std::move(params), help));
	vm.addBifHelp((ns->mName + "." + word).c_str(), nullptr, help);
}

} // namespace

void AddEnvOps();
void AddEnvOps()
{
	vm.addBifHelp(std::string("\n*** env ***"));
	P<Namespace> env = new Namespace("env");
	// SC's argument names, order and defaults (Env.sc)
	const V lin = V(getsym("lin"));
	addEnvPrim(env.get(), "perc", perc_, 2,
		{{"attackTime", .01}, {"releaseTime", 1.}, {"level", 1.}, {"curve", -4.}},
		"(attackTime releaseTime --> env) SC's Env.perc: rises to level, falls to 0. A Form names these and level, curve.");
	addEnvPrim(env.get(), "adsr", adsr_, 4,
		{{"attackTime", .01}, {"decayTime", .3}, {"sustainLevel", .5}, {"releaseTime", 1.}, {"peakLevel", 1.},
			{"curve", -4.}, {"bias", 0.}},
		"(attackTime decayTime sustainLevel releaseTime --> env) SC's Env.adsr: holds peakLevel * sustainLevel until the gate closes. A Form names these and peakLevel, curve, bias.");
	addEnvPrim(env.get(), "asr", asr_, 3,
		{{"attackTime", .01}, {"sustainLevel", 1.}, {"releaseTime", 1.}, {"curve", -4.}},
		"(attackTime sustainLevel releaseTime --> env) SC's Env.asr: holds sustainLevel until the gate closes. A Form names these and curve.");
	addEnvPrim(env.get(), "linen", linen_, 3,
		{{"attackTime", .01}, {"sustainTime", 1.}, {"releaseTime", 1.}, {"level", 1.}, {"curve", lin}},
		"(attackTime sustainTime releaseTime --> env) SC's Env.linen: holds level for sustainTime. A Form names these and level, curve.");
	env->addPrim("new", 3, new_,
		"(levels times curves --> env) SC's Env.new. curves: a real, a UGen, a shape such as 'lin 'exp 'sin, or a list.");
	vm.def("env", V(env));
	vm.addBifHelp("env", nullptr, "(--> namespace) envelopes for envgen and ienvgen.");
}
