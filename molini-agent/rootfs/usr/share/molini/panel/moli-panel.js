var Ie = Object.defineProperty;
var Be = (t, e, n) => e in t ? Ie(t, e, { enumerable: !0, configurable: !0, writable: !0, value: n }) : t[e] = n;
var X = (t, e, n) => Be(t, typeof e != "symbol" ? e + "" : e, n);
var B, w, Ce, P, ce, Se, ze, G, F, A, He, ie, Q, Y, R = {}, T = [], qe = /acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i, q = Array.isArray;
function $(t, e) {
  for (var n in e) t[n] = e[n];
  return t;
}
function ae(t) {
  t && t.parentNode && t.parentNode.removeChild(t);
}
function Ne(t, e, n) {
  var o, i, r, l = {};
  for (r in e) r == "key" ? o = e[r] : r == "ref" ? i = e[r] : l[r] = e[r];
  if (arguments.length > 2 && (l.children = arguments.length > 3 ? B.call(arguments, 2) : n), typeof t == "function" && t.defaultProps != null) for (r in t.defaultProps) l[r] === void 0 && (l[r] = t.defaultProps[r]);
  return W(t, l, o, i, null);
}
function W(t, e, n, o, i) {
  var r = { type: t, props: e, key: n, ref: o, __k: null, __: null, __b: 0, __e: null, __c: null, constructor: void 0, __v: i ?? ++Ce, __i: -1, __u: 0 };
  return i == null && w.vnode != null && w.vnode(r), r;
}
function H(t) {
  return t.children;
}
function E(t, e) {
  this.props = t, this.context = e;
}
function N(t, e) {
  if (e == null) return t.__ ? N(t.__, t.__i + 1) : null;
  for (var n; e < t.__k.length; e++) if ((n = t.__k[e]) != null && n.__e != null) return n.__e;
  return typeof t.type == "function" ? N(t) : null;
}
function Ve(t) {
  if (t.__P && t.__d) {
    var e = t.__v, n = e.__e, o = [], i = [], r = $({}, e);
    r.__v = e.__v + 1, w.vnode && w.vnode(r), le(t.__P, r, e, t.__n, t.__P.namespaceURI, 32 & e.__u ? [n] : null, o, n ?? N(e), !!(32 & e.__u), i), r.__v = e.__v, r.__.__k[r.__i] = r, De(o, r, i), e.__e = e.__ = null, r.__e != n && Le(r);
  }
}
function Le(t) {
  if ((t = t.__) != null && t.__c != null) return t.__e = t.__c.base = null, t.__k.some(function(e) {
    if (e != null && e.__e != null) return t.__e = t.__c.base = e.__e;
  }), Le(t);
}
function de(t) {
  (!t.__d && (t.__d = !0) && P.push(t) && !U.__r++ || ce != w.debounceRendering) && ((ce = w.debounceRendering) || Se)(U);
}
function U() {
  try {
    for (var t, e = 1; P.length; ) P.length > e && P.sort(ze), t = P.shift(), e = P.length, Ve(t);
  } finally {
    P.length = U.__r = 0;
  }
}
function Ae(t, e, n, o, i, r, l, s, d, _, p) {
  var a, h, u, f, y, v, g, m = o && o.__k || T, M = e.length;
  for (d = Xe(n, e, m, d, M), a = 0; a < M; a++) (u = n.__k[a]) != null && (h = u.__i != -1 && m[u.__i] || R, u.__i = a, v = le(t, u, h, i, r, l, s, d, _, p), f = u.__e, u.ref && h.ref != u.ref && (h.ref && se(h.ref, null, u), p.push(u.ref, u.__c || f, u)), y == null && f != null && (y = f), (g = !!(4 & u.__u)) || h.__k === u.__k ? (d = je(u, d, t, g), g && h.__e && (h.__e = null)) : typeof u.type == "function" && v !== void 0 ? d = v : f && (d = f.nextSibling), u.__u &= -7);
  return n.__e = y, d;
}
function Xe(t, e, n, o, i) {
  var r, l, s, d, _, p = n.length, a = p, h = 0;
  for (t.__k = new Array(i), r = 0; r < i; r++) (l = e[r]) != null && typeof l != "boolean" && typeof l != "function" ? (typeof l == "string" || typeof l == "number" || typeof l == "bigint" || l.constructor == String ? l = t.__k[r] = W(null, l, null, null, null) : q(l) ? l = t.__k[r] = W(H, { children: l }, null, null, null) : l.constructor === void 0 && l.__b > 0 ? l = t.__k[r] = W(l.type, l.props, l.key, l.ref ? l.ref : null, l.__v) : t.__k[r] = l, d = r + h, l.__ = t, l.__b = t.__b + 1, s = null, (_ = l.__i = Ge(l, n, d, a)) != -1 && (a--, (s = n[_]) && (s.__u |= 2)), s == null || s.__v == null ? (_ == -1 && (i > p ? h-- : i < p && h++), typeof l.type != "function" && (l.__u |= 4)) : _ != d && (_ == d - 1 ? h-- : _ == d + 1 ? h++ : (_ > d ? h-- : h++, l.__u |= 4))) : t.__k[r] = null;
  if (a) for (r = 0; r < p; r++) (s = n[r]) != null && !(2 & s.__u) && (s.__e == o && (o = N(s)), We(s, s));
  return o;
}
function je(t, e, n, o) {
  var i, r;
  if (typeof t.type == "function") {
    for (i = t.__k, r = 0; i && r < i.length; r++) i[r] && (i[r].__ = t, e = je(i[r], e, n, o));
    return e;
  }
  t.__e != e && (o && (e && t.type && !e.parentNode && (e = N(t)), n.insertBefore(t.__e, e || null)), e = t.__e);
  do
    e = e && e.nextSibling;
  while (e != null && e.nodeType == 8);
  return e;
}
function Ge(t, e, n, o) {
  var i, r, l, s = t.key, d = t.type, _ = e[n], p = _ != null && (2 & _.__u) == 0;
  if (_ === null && s == null || p && s == _.key && d == _.type) return n;
  if (o > (p ? 1 : 0)) {
    for (i = n - 1, r = n + 1; i >= 0 || r < e.length; ) if ((_ = e[l = i >= 0 ? i-- : r++]) != null && !(2 & _.__u) && s == _.key && d == _.type) return l;
  }
  return -1;
}
function ue(t, e, n) {
  e[0] == "-" ? t.setProperty(e, n ?? "") : t[e] = n == null ? "" : typeof n != "number" || qe.test(e) ? n : n + "px";
}
function D(t, e, n, o, i) {
  var r, l;
  e: if (e == "style") if (typeof n == "string") t.style.cssText = n;
  else {
    if (typeof o == "string" && (t.style.cssText = o = ""), o) for (e in o) n && e in n || ue(t.style, e, "");
    if (n) for (e in n) o && n[e] == o[e] || ue(t.style, e, n[e]);
  }
  else if (e[0] == "o" && e[1] == "n") r = e != (e = e.replace(He, "$1")), l = e.toLowerCase(), e = l in t || e == "onFocusOut" || e == "onFocusIn" ? l.slice(2) : e.slice(2), t.l || (t.l = {}), t.l[e + r] = n, n ? o ? n[A] = o[A] : (n[A] = ie, t.addEventListener(e, r ? Y : Q, r)) : t.removeEventListener(e, r ? Y : Q, r);
  else {
    if (i == "http://www.w3.org/2000/svg") e = e.replace(/xlink(H|:h)/, "h").replace(/sName$/, "s");
    else if (e != "width" && e != "height" && e != "href" && e != "list" && e != "form" && e != "tabIndex" && e != "download" && e != "rowSpan" && e != "colSpan" && e != "role" && e != "popover" && e in t) try {
      t[e] = n ?? "";
      break e;
    } catch {
    }
    typeof n == "function" || (n == null || n === !1 && e[4] != "-" ? t.removeAttribute(e) : t.setAttribute(e, e == "popover" && n == 1 ? "" : n));
  }
}
function pe(t) {
  return function(e) {
    if (this.l) {
      var n = this.l[e.type + t];
      if (e[F] == null) e[F] = ie++;
      else if (e[F] < n[A]) return;
      return n(w.event ? w.event(e) : e);
    }
  };
}
function le(t, e, n, o, i, r, l, s, d, _) {
  var p, a, h, u, f, y, v, g, m, M, C, L, _e, j, V, k = e.type;
  if (e.constructor !== void 0) return null;
  128 & n.__u && (d = !!(32 & n.__u), r = [s = e.__e = n.__e]), (p = w.__b) && p(e);
  e: if (typeof k == "function") try {
    if (g = e.props, m = k.prototype && k.prototype.render, M = (p = k.contextType) && o[p.__c], C = p ? M ? M.props.value : p.__ : o, n.__c ? v = (a = e.__c = n.__c).__ = a.__E : (m ? e.__c = a = new k(g, C) : (e.__c = a = new E(g, C), a.constructor = k, a.render = Je), M && M.sub(a), a.state || (a.state = {}), a.__n = o, h = a.__d = !0, a.__h = [], a._sb = []), m && a.__s == null && (a.__s = a.state), m && k.getDerivedStateFromProps != null && (a.__s == a.state && (a.__s = $({}, a.__s)), $(a.__s, k.getDerivedStateFromProps(g, a.__s))), u = a.props, f = a.state, a.__v = e, h) m && k.getDerivedStateFromProps == null && a.componentWillMount != null && a.componentWillMount(), m && a.componentDidMount != null && a.__h.push(a.componentDidMount);
    else {
      if (m && k.getDerivedStateFromProps == null && g !== u && a.componentWillReceiveProps != null && a.componentWillReceiveProps(g, C), e.__v == n.__v || !a.__e && a.shouldComponentUpdate != null && a.shouldComponentUpdate(g, a.__s, C) === !1) {
        e.__v != n.__v && (a.props = g, a.state = a.__s, a.__d = !1), e.__e = n.__e, e.__k = n.__k, e.__k.some(function(S) {
          S && (S.__ = e);
        }), T.push.apply(a.__h, a._sb), a._sb = [], a.__h.length && l.push(a);
        break e;
      }
      a.componentWillUpdate != null && a.componentWillUpdate(g, a.__s, C), m && a.componentDidUpdate != null && a.__h.push(function() {
        a.componentDidUpdate(u, f, y);
      });
    }
    if (a.context = C, a.props = g, a.__P = t, a.__e = !1, L = w.__r, _e = 0, m) a.state = a.__s, a.__d = !1, L && L(e), p = a.render(a.props, a.state, a.context), T.push.apply(a.__h, a._sb), a._sb = [];
    else do
      a.__d = !1, L && L(e), p = a.render(a.props, a.state, a.context), a.state = a.__s;
    while (a.__d && ++_e < 25);
    a.state = a.__s, a.getChildContext != null && (o = $($({}, o), a.getChildContext())), m && !h && a.getSnapshotBeforeUpdate != null && (y = a.getSnapshotBeforeUpdate(u, f)), j = p != null && p.type === H && p.key == null ? Fe(p.props.children) : p, s = Ae(t, q(j) ? j : [j], e, n, o, i, r, l, s, d, _), a.base = e.__e, e.__u &= -161, a.__h.length && l.push(a), v && (a.__E = a.__ = null);
  } catch (S) {
    if (e.__v = null, d || r != null) if (S.then) {
      for (e.__u |= d ? 160 : 128; s && s.nodeType == 8 && s.nextSibling; ) s = s.nextSibling;
      r[r.indexOf(s)] = null, e.__e = s;
    } else {
      for (V = r.length; V--; ) ae(r[V]);
      Z(e);
    }
    else e.__e = n.__e, e.__k = n.__k, S.then || Z(e);
    w.__e(S, e, n);
  }
  else r == null && e.__v == n.__v ? (e.__k = n.__k, e.__e = n.__e) : s = e.__e = Ke(n.__e, e, n, o, i, r, l, d, _);
  return (p = w.diffed) && p(e), 128 & e.__u ? void 0 : s;
}
function Z(t) {
  t && (t.__c && (t.__c.__e = !0), t.__k && t.__k.some(Z));
}
function De(t, e, n) {
  for (var o = 0; o < n.length; o++) se(n[o], n[++o], n[++o]);
  w.__c && w.__c(e, t), t.some(function(i) {
    try {
      t = i.__h, i.__h = [], t.some(function(r) {
        r.call(i);
      });
    } catch (r) {
      w.__e(r, i.__v);
    }
  });
}
function Fe(t) {
  return typeof t != "object" || t == null || t.__b > 0 ? t : q(t) ? t.map(Fe) : t.constructor !== void 0 ? null : $({}, t);
}
function Ke(t, e, n, o, i, r, l, s, d) {
  var _, p, a, h, u, f, y, v = n.props || R, g = e.props, m = e.type;
  if (m == "svg" ? i = "http://www.w3.org/2000/svg" : m == "math" ? i = "http://www.w3.org/1998/Math/MathML" : i || (i = "http://www.w3.org/1999/xhtml"), r != null) {
    for (_ = 0; _ < r.length; _++) if ((u = r[_]) && "setAttribute" in u == !!m && (m ? u.localName == m : u.nodeType == 3)) {
      t = u, r[_] = null;
      break;
    }
  }
  if (t == null) {
    if (m == null) return document.createTextNode(g);
    t = document.createElementNS(i, m, g.is && g), s && (w.__m && w.__m(e, r), s = !1), r = null;
  }
  if (m == null) v === g || s && t.data == g || (t.data = g);
  else {
    if (r = m == "textarea" && g.defaultValue != null ? null : r && B.call(t.childNodes), !s && r != null) for (v = {}, _ = 0; _ < t.attributes.length; _++) v[(u = t.attributes[_]).name] = u.value;
    for (_ in v) u = v[_], _ == "dangerouslySetInnerHTML" ? a = u : _ == "children" || _ in g || _ == "value" && "defaultValue" in g || _ == "checked" && "defaultChecked" in g || D(t, _, null, u, i);
    for (_ in g) u = g[_], _ == "children" ? h = u : _ == "dangerouslySetInnerHTML" ? p = u : _ == "value" ? f = u : _ == "checked" ? y = u : s && typeof u != "function" || v[_] === u || D(t, _, u, v[_], i);
    if (p) s || a && (p.__html == a.__html || p.__html == t.innerHTML) || (t.innerHTML = p.__html), e.__k = [];
    else if (a && (t.innerHTML = ""), Ae(e.type == "template" ? t.content : t, q(h) ? h : [h], e, n, o, m == "foreignObject" ? "http://www.w3.org/1999/xhtml" : i, r, l, r ? r[0] : n.__k && N(n, 0), s, d), r != null) for (_ = r.length; _--; ) ae(r[_]);
    s && m != "textarea" || (_ = "value", m == "progress" && f == null ? t.removeAttribute("value") : f != null && (f !== t[_] || m == "progress" && !f || m == "option" && f != v[_]) && D(t, _, f, v[_], i), _ = "checked", y != null && y != t[_] && D(t, _, y, v[_], i));
  }
  return t;
}
function se(t, e, n) {
  try {
    if (typeof t == "function") {
      var o = typeof t.__u == "function";
      o && t.__u(), o && e == null || (t.__u = t(e));
    } else t.current = e;
  } catch (i) {
    w.__e(i, n);
  }
}
function We(t, e, n) {
  var o, i;
  if (w.unmount && w.unmount(t), (o = t.ref) && (o.current && o.current != t.__e || se(o, null, e)), (o = t.__c) != null) {
    if (o.componentWillUnmount) try {
      o.componentWillUnmount();
    } catch (r) {
      w.__e(r, e);
    }
    o.base = o.__P = null;
  }
  if (o = t.__k) for (i = 0; i < o.length; i++) o[i] && We(o[i], e, n || typeof t.type != "function");
  n || ae(t.__e), t.__c = t.__ = t.__e = void 0;
}
function Je(t, e, n) {
  return this.constructor(t, n);
}
function Qe(t, e, n) {
  var o, i, r, l;
  e == document && (e = document.documentElement), w.__ && w.__(t, e), i = (o = !1) ? null : e.__k, r = [], l = [], le(e, t = e.__k = Ne(H, null, [t]), i || R, R, e.namespaceURI, i ? null : e.firstChild ? B.call(e.childNodes) : null, r, i ? i.__e : e.firstChild, o, l), De(r, t, l);
}
B = T.slice, w = { __e: function(t, e, n, o) {
  for (var i, r, l; e = e.__; ) if ((i = e.__c) && !i.__) try {
    if ((r = i.constructor) && r.getDerivedStateFromError != null && (i.setState(r.getDerivedStateFromError(t)), l = i.__d), i.componentDidCatch != null && (i.componentDidCatch(t, o || {}), l = i.__d), l) return i.__E = i;
  } catch (s) {
    t = s;
  }
  throw t;
} }, Ce = 0, E.prototype.setState = function(t, e) {
  var n;
  n = this.__s != null && this.__s != this.state ? this.__s : this.__s = $({}, this.state), typeof t == "function" && (t = t($({}, n), this.props)), t && $(n, t), t != null && this.__v && (e && this._sb.push(e), de(this));
}, E.prototype.forceUpdate = function(t) {
  this.__v && (this.__e = !0, t && this.__h.push(t), de(this));
}, E.prototype.render = H, P = [], Se = typeof Promise == "function" ? Promise.prototype.then.bind(Promise.resolve()) : setTimeout, ze = function(t, e) {
  return t.__v.__b - e.__v.__b;
}, U.__r = 0, G = Math.random().toString(8), F = "__d" + G, A = "__a" + G, He = /(PointerCapture)$|Capture$/i, ie = 0, Q = pe(!1), Y = pe(!0);
var Ye = 0;
function c(t, e, n, o, i, r) {
  e || (e = {});
  var l, s, d = e;
  if ("ref" in d) for (s in d = {}, e) s == "ref" ? l = e[s] : d[s] = e[s];
  var _ = { type: t, props: d, key: n, ref: l, __k: null, __: null, __b: 0, __e: null, __c: null, constructor: void 0, __v: --Ye, __i: -1, __u: 0, __source: i, __self: r };
  if (typeof t == "function" && (l = t.defaultProps)) for (s in l) d[s] === void 0 && (d[s] = l[s]);
  return w.vnode && w.vnode(_), _;
}
function z(t, e) {
  const n = t.states[e];
  if (!n) return null;
  const o = Number(n.state);
  return Number.isFinite(o) ? o : null;
}
function Ee(t) {
  return t == null ? "—" : Math.round(t).toLocaleString("fr-FR");
}
function ee(t) {
  return t == null ? "—" : t.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}
function he({
  value: t,
  max: e,
  label: n,
  unit: o = "W",
  color: i,
  mutedLabel: r = "non suivie"
}) {
  const l = t != null, s = t ?? 0, d = e > 0 ? Math.max(0, Math.min(1, s / e)) : 0, _ = 80, p = 100, a = 100, h = Math.PI * _, u = `M${p - _},${a} A${_},${_} 0 0 1 ${p + _},${a}`;
  return /* @__PURE__ */ c("div", { class: "rounded-xl bg-moli-surface border border-moli-border p-4", children: [
    /* @__PURE__ */ c("div", { class: "text-sm text-moli-muted mb-1", children: n }),
    /* @__PURE__ */ c("svg", { viewBox: "0 0 200 116", class: "block w-full max-w-[260px] mx-auto", children: [
      /* @__PURE__ */ c("path", { d: u, fill: "none", stroke: "#2a313d", "stroke-width": "13", "stroke-linecap": "round" }),
      l && /* @__PURE__ */ c(
        "path",
        {
          d: u,
          fill: "none",
          stroke: i,
          "stroke-width": "13",
          "stroke-linecap": "round",
          "stroke-dasharray": h,
          "stroke-dashoffset": h * (1 - d)
        }
      ),
      /* @__PURE__ */ c(
        "text",
        {
          x: "100",
          y: "93",
          "text-anchor": "middle",
          style: { fill: "#e6e9ef", fontSize: "30px", fontWeight: 500 },
          children: l ? Ee(t) : "—"
        }
      ),
      /* @__PURE__ */ c("text", { x: "100", y: "110", "text-anchor": "middle", style: { fill: "#9aa3b2", fontSize: "12px" }, children: l ? o : r })
    ] })
  ] });
}
function Ze({ hass: t }) {
  const e = z(t, "sensor.molini_solaire_production"), n = z(t, "sensor.molini_consommation_maison"), o = z(t, "sensor.molini_solaire_production_aujourd_hui");
  return /* @__PURE__ */ c("div", { class: "space-y-3", children: [
    /* @__PURE__ */ c("div", { class: "grid grid-cols-1 sm:grid-cols-2 gap-3", children: [
      /* @__PURE__ */ c(he, { value: e, max: 5e3, label: "Production solaire", color: "#1d9e75" }),
      /* @__PURE__ */ c(
        he,
        {
          value: n,
          max: 6e3,
          label: "Consommation maison",
          color: "#378add",
          mutedLabel: "non suivie"
        }
      )
    ] }),
    /* @__PURE__ */ c("div", { class: "rounded-lg bg-moli-surface border border-moli-border px-4 py-3 flex items-baseline justify-between", children: [
      /* @__PURE__ */ c("span", { class: "text-sm text-moli-muted", children: "Produit aujourd'hui" }),
      /* @__PURE__ */ c("span", { class: "text-xl font-medium", children: [
        ee(o),
        /* @__PURE__ */ c("span", { class: "text-xs text-moli-muted", children: " kWh" })
      ] })
    ] })
  ] });
}
const K = /^(?<prefix>.+?)_pv(?<n>\d+)(?:_power)?$/, et = /(?:^|\.)inverter(?:_\d+)?$/;
function tt(t) {
  var n;
  const e = {};
  for (const o of t) {
    if (!o.startsWith("sensor.")) continue;
    const i = K.exec(o);
    i != null && i.groups && (e[n = i.groups.prefix] ?? (e[n] = [])).push(o);
  }
  for (const o of Object.keys(e))
    e[o].sort(
      (i, r) => Number(K.exec(i).groups.n) - Number(K.exec(r).groups.n)
    );
  return e;
}
function nt(t) {
  const e = t.toLowerCase();
  return e.includes("izypower") || e.includes("micro");
}
function rt(t, e) {
  return `${nt(t) ? "Micro-onduleur" : "Onduleur"} ${e + 1}`;
}
function ot(t) {
  const e = t.toLowerCase();
  return e.includes("izypower") ? "izypower" : et.test(e) ? "solarman" : null;
}
const it = {
  solarman: "Onduleur SolarMan",
  izypower: "Micro-onduleurs IzyPower"
};
function at(t) {
  const e = tt(t), n = /* @__PURE__ */ new Map();
  let o = 0;
  for (const r of Object.keys(e).sort()) {
    const l = ot(r), s = l ?? `other:${r}`;
    n.has(s) || n.set(s, { label: l ? it[l] : rt(r, o++), eids: [] }), n.get(s).eids.push(...e[r]);
  }
  const i = (r) => r === "solarman" ? 0 : r === "izypower" ? 1 : 2;
  return [...n.entries()].sort((r, l) => i(r[0]) - i(l[0]) || r[0].localeCompare(l[0])).map(([r, l]) => ({
    key: r,
    label: l.label,
    panels: l.eids.map((s, d) => ({ name: `P${d + 1}`, eid: s }))
  }));
}
function lt({
  id: t,
  name: e,
  watts: n,
  max: o
}) {
  const i = n == null ? 0 : Math.max(0, Math.min(1, n / o)), r = n != null && i > 0 && i < 0.2, l = 56 * i, s = `pm-${t}`;
  return /* @__PURE__ */ c("div", { "data-panel-tile": !0, class: "flex flex-col items-center rounded-lg bg-moli-surface2 p-2", children: [
    /* @__PURE__ */ c("svg", { viewBox: "0 0 100 64", class: "w-full", children: [
      /* @__PURE__ */ c("clipPath", { id: s, children: /* @__PURE__ */ c("rect", { x: "6", y: "4", width: "88", height: "56", rx: "3" }) }),
      /* @__PURE__ */ c("rect", { x: "6", y: "4", width: "88", height: "56", rx: "3", fill: "#0e1b2a" }),
      /* @__PURE__ */ c(
        "rect",
        {
          x: "6",
          y: 60 - l,
          width: "88",
          height: l,
          fill: r ? "#ba7517" : "#1d9e75",
          "fill-opacity": "0.62",
          "clip-path": `url(#${s})`
        }
      ),
      /* @__PURE__ */ c("g", { stroke: "#243044", "stroke-width": "1.3", children: [
        /* @__PURE__ */ c("line", { x1: "28", y1: "4", x2: "28", y2: "60" }),
        /* @__PURE__ */ c("line", { x1: "50", y1: "4", x2: "50", y2: "60" }),
        /* @__PURE__ */ c("line", { x1: "72", y1: "4", x2: "72", y2: "60" }),
        /* @__PURE__ */ c("line", { x1: "6", y1: "32", x2: "94", y2: "32" })
      ] }),
      /* @__PURE__ */ c("rect", { x: "6", y: "4", width: "88", height: "56", rx: "3", fill: "none", stroke: "#3a4456", "stroke-width": "1.5" })
    ] }),
    /* @__PURE__ */ c("div", { class: "mt-1 text-[12px] text-moli-muted", children: e }),
    /* @__PURE__ */ c("div", { class: "text-[14px] font-medium leading-tight", children: [
      Ee(n),
      /* @__PURE__ */ c("span", { class: "text-[10px] text-moli-muted", children: " W" })
    ] })
  ] });
}
const st = 400;
function _t({ hass: t }) {
  const e = at(Object.keys(t.states));
  return e.length === 0 ? null : /* @__PURE__ */ c("div", { class: "grid grid-cols-1 md:grid-cols-2 gap-3", children: e.map((n) => /* @__PURE__ */ c("div", { class: "rounded-xl bg-moli-surface border border-moli-border p-3.5", children: [
    /* @__PURE__ */ c("div", { class: "text-[13px] text-moli-muted mb-2.5", children: [
      n.label,
      " ",
      /* @__PURE__ */ c("span", { class: "text-moli-muted/70", children: [
        "· ",
        n.panels.length,
        " panneaux"
      ] })
    ] }),
    /* @__PURE__ */ c("div", { class: "grid grid-cols-3 gap-2", children: n.panels.map((o) => /* @__PURE__ */ c(
      lt,
      {
        id: o.eid.replace(/[^a-z0-9]/gi, ""),
        name: o.name,
        watts: z(t, o.eid),
        max: st
      },
      o.eid
    )) })
  ] }, n.key)) });
}
function ct({ hass: t }) {
  const e = z(t, "sensor.molini_index_hc"), n = z(t, "sensor.molini_index_hp");
  return /* @__PURE__ */ c("div", { class: "rounded-xl bg-moli-surface border border-moli-border px-4", children: [
    /* @__PURE__ */ c(fe, { label: "Index heures creuses", value: ee(e), unit: "kWh", border: !0 }),
    /* @__PURE__ */ c(fe, { label: "Index heures pleines", value: ee(n), unit: "kWh" })
  ] });
}
function fe({
  label: t,
  value: e,
  unit: n,
  border: o
}) {
  return /* @__PURE__ */ c(
    "div",
    {
      class: `flex items-center justify-between py-2.5 ${o ? "border-b border-moli-border" : ""}`,
      children: [
        /* @__PURE__ */ c("span", { class: "text-sm text-moli-muted", children: t }),
        /* @__PURE__ */ c("span", { class: "text-[15px] font-medium", children: [
          e,
          " ",
          n
        ] })
      ]
    }
  );
}
var I, b, J, me, te = 0, Oe = [], x = w, ge = x.__b, we = x.__r, be = x.diffed, xe = x.__c, ve = x.unmount, ye = x.__;
function Re(t, e) {
  x.__h && x.__h(b, t, te || e), te = 0;
  var n = b.__H || (b.__H = { __: [], __h: [] });
  return t >= n.__.length && n.__.push({}), n.__[t];
}
function ke(t) {
  return te = 1, dt(Te, t);
}
function dt(t, e, n) {
  var o = Re(I++, 2);
  if (o.t = t, !o.__c && (o.__ = [Te(void 0, e), function(s) {
    var d = o.__N ? o.__N[0] : o.__[0], _ = o.t(d, s);
    d !== _ && (o.__N = [_, o.__[1]], o.__c.setState({}));
  }], o.__c = b, !b.__f)) {
    var i = function(s, d, _) {
      if (!o.__c.__H) return !0;
      var p = o.__c.__H.__.filter(function(h) {
        return h.__c;
      });
      if (p.every(function(h) {
        return !h.__N;
      })) return !r || r.call(this, s, d, _);
      var a = o.__c.props !== s;
      return p.some(function(h) {
        if (h.__N) {
          var u = h.__[0];
          h.__ = h.__N, h.__N = void 0, u !== h.__[0] && (a = !0);
        }
      }), r && r.call(this, s, d, _) || a;
    };
    b.__f = !0;
    var r = b.shouldComponentUpdate, l = b.componentWillUpdate;
    b.componentWillUpdate = function(s, d, _) {
      if (this.__e) {
        var p = r;
        r = void 0, i(s, d, _), r = p;
      }
      l && l.call(this, s, d, _);
    }, b.shouldComponentUpdate = i;
  }
  return o.__N || o.__;
}
function ut(t, e) {
  var n = Re(I++, 3);
  !x.__s && ft(n.__H, e) && (n.__ = t, n.u = e, b.__H.__h.push(n));
}
function pt() {
  for (var t; t = Oe.shift(); ) {
    var e = t.__H;
    if (t.__P && e) try {
      e.__h.some(O), e.__h.some(ne), e.__h = [];
    } catch (n) {
      e.__h = [], x.__e(n, t.__v);
    }
  }
}
x.__b = function(t) {
  b = null, ge && ge(t);
}, x.__ = function(t, e) {
  t && e.__k && e.__k.__m && (t.__m = e.__k.__m), ye && ye(t, e);
}, x.__r = function(t) {
  we && we(t), I = 0;
  var e = (b = t.__c).__H;
  e && (J === b ? (e.__h = [], b.__h = [], e.__.some(function(n) {
    n.__N && (n.__ = n.__N), n.u = n.__N = void 0;
  })) : (e.__h.some(O), e.__h.some(ne), e.__h = [], I = 0)), J = b;
}, x.diffed = function(t) {
  be && be(t);
  var e = t.__c;
  e && e.__H && (e.__H.__h.length && (Oe.push(e) !== 1 && me === x.requestAnimationFrame || ((me = x.requestAnimationFrame) || ht)(pt)), e.__H.__.some(function(n) {
    n.u && (n.__H = n.u), n.u = void 0;
  })), J = b = null;
}, x.__c = function(t, e) {
  e.some(function(n) {
    try {
      n.__h.some(O), n.__h = n.__h.filter(function(o) {
        return !o.__ || ne(o);
      });
    } catch (o) {
      e.some(function(i) {
        i.__h && (i.__h = []);
      }), e = [], x.__e(o, n.__v);
    }
  }), xe && xe(t, e);
}, x.unmount = function(t) {
  ve && ve(t);
  var e, n = t.__c;
  n && n.__H && (n.__H.__.some(function(o) {
    try {
      O(o);
    } catch (i) {
      e = i;
    }
  }), n.__H = void 0, e && x.__e(e, n.__v));
};
var $e = typeof requestAnimationFrame == "function";
function ht(t) {
  var e, n = function() {
    clearTimeout(o), $e && cancelAnimationFrame(e), setTimeout(t);
  }, o = setTimeout(n, 35);
  $e && (e = requestAnimationFrame(n));
}
function O(t) {
  var e = b, n = t.__c;
  typeof n == "function" && (t.__c = void 0, n()), b = e;
}
function ne(t) {
  var e = b;
  t.__c = t.__(), b = e;
}
function ft(t, e) {
  return !t || t.length !== e.length || e.some(function(n, o) {
    return n !== t[o];
  });
}
function Te(t, e) {
  return typeof e == "function" ? e(t) : e;
}
async function Me(t, e, n = 24, o = "solar") {
  if (t.callWS)
    try {
      const i = /* @__PURE__ */ new Date(), r = new Date(i.getTime() - n * 36e5), l = await t.callWS({
        type: "history/history_during_period",
        start_time: r.toISOString(),
        end_time: i.toISOString(),
        entity_ids: [e],
        minimal_response: !0,
        no_attributes: !0
      }), s = l == null ? void 0 : l[e];
      return Array.isArray(s) ? s.map((d) => ({
        t: d.lu != null ? d.lu * 1e3 : Date.parse(d.last_updated ?? d.last_changed ?? ""),
        v: Number(d.s ?? d.state)
      })).filter((d) => Number.isFinite(d.v) && Number.isFinite(d.t)) : [];
    } catch {
      return [];
    }
  return o === "load" ? gt(n) : mt(n);
}
function mt(t) {
  return Ue(t, (e) => Math.max(0, Math.exp(-(((e - 13) / 3.2) ** 2)) * 4600 - 60));
}
function gt(t) {
  return Ue(
    t,
    (e) => 280 + Math.exp(-(((e - 8) / 1.6) ** 2)) * 850 + Math.exp(-(((e - 20) / 2.2) ** 2)) * 1500
  );
}
function Ue(t, e) {
  const n = [], o = Date.now();
  for (let i = t * 4; i >= 0; i--) {
    const r = o - i * 15 * 6e4, l = new Date(r), s = l.getHours() + l.getMinutes() / 60;
    n.push({ t: r, v: Math.max(0, Math.round(e(s))) });
  }
  return n;
}
const re = "#1d9e75", oe = "#378add";
function wt({ hass: t }) {
  const [e, n] = ke([]), [o, i] = ke([]);
  ut(() => {
    let s = !0;
    return Me(t, "sensor.molini_solaire_production", 24, "solar").then((d) => {
      s && n(d);
    }), Me(t, "sensor.molini_consommation_maison", 24, "load").then((d) => {
      s && i(d);
    }), () => {
      s = !1;
    };
  }, []);
  const r = o.length >= 2, l = e.length >= 2 || r;
  return /* @__PURE__ */ c("div", { class: "rounded-xl bg-moli-surface border border-moli-border p-4", children: [
    /* @__PURE__ */ c("div", { class: "mb-2 flex items-center justify-between", children: [
      /* @__PURE__ */ c("div", { class: "text-[13px] text-moli-muted", children: "24 dernières heures" }),
      /* @__PURE__ */ c("div", { class: "flex items-center gap-3 text-[12px] text-moli-muted", children: [
        /* @__PURE__ */ c(Pe, { color: re, label: "Production" }),
        r && /* @__PURE__ */ c(Pe, { color: oe, label: "Consommation" })
      ] })
    ] }),
    l ? /* @__PURE__ */ c(bt, { prod: e, conso: o }) : /* @__PURE__ */ c("div", { class: "flex h-40 items-center justify-center text-sm text-moli-muted", children: "Pas encore de données" })
  ] });
}
function Pe({ color: t, label: e }) {
  return /* @__PURE__ */ c("span", { class: "flex items-center gap-1.5", children: [
    /* @__PURE__ */ c("span", { class: "inline-block h-2.5 w-2.5 rounded-sm", style: { background: t } }),
    e
  ] });
}
function bt({ prod: t, conso: e }) {
  const r = [...t, ...e], l = r.map((f) => f.t), s = Math.min(...l), d = Math.max(...l), _ = Math.max(100, ...r.map((f) => f.v)), p = (f) => 4 + (f - s) / (d - s || 1) * (720 - 2 * 4), a = (f) => 156 - f / _ * (160 - 2 * 4), h = (f) => f.map((y, v) => `${v ? "L" : "M"}${p(y.t).toFixed(1)},${a(y.v).toFixed(1)}`).join(" "), u = (f) => f.length < 2 ? "" : `${h(f)} L${p(f[f.length - 1].t).toFixed(1)},156 L${p(f[0].t).toFixed(1)},156 Z`;
  return /* @__PURE__ */ c(
    "svg",
    {
      viewBox: "0 0 720 160",
      class: "h-40 w-full",
      preserveAspectRatio: "none",
      role: "img",
      "aria-label": "Production et consommation des dernières 24 heures",
      children: [
        t.length >= 2 && /* @__PURE__ */ c(H, { children: [
          /* @__PURE__ */ c("path", { d: u(t), fill: re, "fill-opacity": "0.15" }),
          /* @__PURE__ */ c(
            "path",
            {
              d: h(t),
              fill: "none",
              stroke: re,
              "stroke-width": "2",
              "stroke-linejoin": "round",
              "stroke-linecap": "round",
              "vector-effect": "non-scaling-stroke"
            }
          )
        ] }),
        e.length >= 2 && /* @__PURE__ */ c(H, { children: [
          /* @__PURE__ */ c("path", { d: u(e), fill: oe, "fill-opacity": "0.12" }),
          /* @__PURE__ */ c(
            "path",
            {
              d: h(e),
              fill: "none",
              stroke: oe,
              "stroke-width": "2",
              "stroke-linejoin": "round",
              "stroke-linecap": "round",
              "vector-effect": "non-scaling-stroke"
            }
          )
        ] })
      ]
    }
  );
}
function xt({ hass: t }) {
  return /* @__PURE__ */ c("div", { class: "min-h-screen bg-moli-bg text-moli-text", children: /* @__PURE__ */ c("div", { class: "mx-auto max-w-5xl px-4 py-6 space-y-5", children: [
    /* @__PURE__ */ c(Ze, { hass: t }),
    /* @__PURE__ */ c(_t, { hass: t }),
    /* @__PURE__ */ c(wt, { hass: t }),
    /* @__PURE__ */ c(ct, { hass: t })
  ] }) });
}
function vt({ hass: t }) {
  return /* @__PURE__ */ c(xt, { hass: t });
}
const yt = '*,:before,:after{--tw-border-spacing-x: 0;--tw-border-spacing-y: 0;--tw-translate-x: 0;--tw-translate-y: 0;--tw-rotate: 0;--tw-skew-x: 0;--tw-skew-y: 0;--tw-scale-x: 1;--tw-scale-y: 1;--tw-pan-x: ;--tw-pan-y: ;--tw-pinch-zoom: ;--tw-scroll-snap-strictness: proximity;--tw-gradient-from-position: ;--tw-gradient-via-position: ;--tw-gradient-to-position: ;--tw-ordinal: ;--tw-slashed-zero: ;--tw-numeric-figure: ;--tw-numeric-spacing: ;--tw-numeric-fraction: ;--tw-ring-inset: ;--tw-ring-offset-width: 0px;--tw-ring-offset-color: #fff;--tw-ring-color: rgb(59 130 246 / .5);--tw-ring-offset-shadow: 0 0 #0000;--tw-ring-shadow: 0 0 #0000;--tw-shadow: 0 0 #0000;--tw-shadow-colored: 0 0 #0000;--tw-blur: ;--tw-brightness: ;--tw-contrast: ;--tw-grayscale: ;--tw-hue-rotate: ;--tw-invert: ;--tw-saturate: ;--tw-sepia: ;--tw-drop-shadow: ;--tw-backdrop-blur: ;--tw-backdrop-brightness: ;--tw-backdrop-contrast: ;--tw-backdrop-grayscale: ;--tw-backdrop-hue-rotate: ;--tw-backdrop-invert: ;--tw-backdrop-opacity: ;--tw-backdrop-saturate: ;--tw-backdrop-sepia: ;--tw-contain-size: ;--tw-contain-layout: ;--tw-contain-paint: ;--tw-contain-style: }::backdrop{--tw-border-spacing-x: 0;--tw-border-spacing-y: 0;--tw-translate-x: 0;--tw-translate-y: 0;--tw-rotate: 0;--tw-skew-x: 0;--tw-skew-y: 0;--tw-scale-x: 1;--tw-scale-y: 1;--tw-pan-x: ;--tw-pan-y: ;--tw-pinch-zoom: ;--tw-scroll-snap-strictness: proximity;--tw-gradient-from-position: ;--tw-gradient-via-position: ;--tw-gradient-to-position: ;--tw-ordinal: ;--tw-slashed-zero: ;--tw-numeric-figure: ;--tw-numeric-spacing: ;--tw-numeric-fraction: ;--tw-ring-inset: ;--tw-ring-offset-width: 0px;--tw-ring-offset-color: #fff;--tw-ring-color: rgb(59 130 246 / .5);--tw-ring-offset-shadow: 0 0 #0000;--tw-ring-shadow: 0 0 #0000;--tw-shadow: 0 0 #0000;--tw-shadow-colored: 0 0 #0000;--tw-blur: ;--tw-brightness: ;--tw-contrast: ;--tw-grayscale: ;--tw-hue-rotate: ;--tw-invert: ;--tw-saturate: ;--tw-sepia: ;--tw-drop-shadow: ;--tw-backdrop-blur: ;--tw-backdrop-brightness: ;--tw-backdrop-contrast: ;--tw-backdrop-grayscale: ;--tw-backdrop-hue-rotate: ;--tw-backdrop-invert: ;--tw-backdrop-opacity: ;--tw-backdrop-saturate: ;--tw-backdrop-sepia: ;--tw-contain-size: ;--tw-contain-layout: ;--tw-contain-paint: ;--tw-contain-style: }*,:before,:after{box-sizing:border-box;border-width:0;border-style:solid;border-color:#e5e7eb}:before,:after{--tw-content: ""}html,:host{line-height:1.5;-webkit-text-size-adjust:100%;-moz-tab-size:4;-o-tab-size:4;tab-size:4;font-family:ui-sans-serif,system-ui,sans-serif,"Apple Color Emoji","Segoe UI Emoji",Segoe UI Symbol,"Noto Color Emoji";font-feature-settings:normal;font-variation-settings:normal;-webkit-tap-highlight-color:transparent}body{margin:0;line-height:inherit}hr{height:0;color:inherit;border-top-width:1px}abbr:where([title]){-webkit-text-decoration:underline dotted;text-decoration:underline dotted}h1,h2,h3,h4,h5,h6{font-size:inherit;font-weight:inherit}a{color:inherit;text-decoration:inherit}b,strong{font-weight:bolder}code,kbd,samp,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,Courier New,monospace;font-feature-settings:normal;font-variation-settings:normal;font-size:1em}small{font-size:80%}sub,sup{font-size:75%;line-height:0;position:relative;vertical-align:baseline}sub{bottom:-.25em}sup{top:-.5em}table{text-indent:0;border-color:inherit;border-collapse:collapse}button,input,optgroup,select,textarea{font-family:inherit;font-feature-settings:inherit;font-variation-settings:inherit;font-size:100%;font-weight:inherit;line-height:inherit;letter-spacing:inherit;color:inherit;margin:0;padding:0}button,select{text-transform:none}button,input:where([type=button]),input:where([type=reset]),input:where([type=submit]){-webkit-appearance:button;background-color:transparent;background-image:none}:-moz-focusring{outline:auto}:-moz-ui-invalid{box-shadow:none}progress{vertical-align:baseline}::-webkit-inner-spin-button,::-webkit-outer-spin-button{height:auto}[type=search]{-webkit-appearance:textfield;outline-offset:-2px}::-webkit-search-decoration{-webkit-appearance:none}::-webkit-file-upload-button{-webkit-appearance:button;font:inherit}summary{display:list-item}blockquote,dl,dd,h1,h2,h3,h4,h5,h6,hr,figure,p,pre{margin:0}fieldset{margin:0;padding:0}legend{padding:0}ol,ul,menu{list-style:none;margin:0;padding:0}dialog{padding:0}textarea{resize:vertical}input::-moz-placeholder,textarea::-moz-placeholder{opacity:1;color:#9ca3af}input::placeholder,textarea::placeholder{opacity:1;color:#9ca3af}button,[role=button]{cursor:pointer}:disabled{cursor:default}img,svg,video,canvas,audio,iframe,embed,object{display:block;vertical-align:middle}img,video{max-width:100%;height:auto}[hidden]:where(:not([hidden=until-found])){display:none}.mx-auto{margin-left:auto;margin-right:auto}.mb-1{margin-bottom:.25rem}.mb-2{margin-bottom:.5rem}.mb-2\\.5{margin-bottom:.625rem}.mt-1{margin-top:.25rem}.block{display:block}.inline-block{display:inline-block}.inline{display:inline}.flex{display:flex}.grid{display:grid}.h-2\\.5{height:.625rem}.h-40{height:10rem}.min-h-screen{min-height:100vh}.w-2\\.5{width:.625rem}.w-full{width:100%}.max-w-5xl{max-width:64rem}.max-w-\\[260px\\]{max-width:260px}.grid-cols-1{grid-template-columns:repeat(1,minmax(0,1fr))}.grid-cols-3{grid-template-columns:repeat(3,minmax(0,1fr))}.flex-col{flex-direction:column}.items-center{align-items:center}.items-baseline{align-items:baseline}.justify-center{justify-content:center}.justify-between{justify-content:space-between}.gap-1\\.5{gap:.375rem}.gap-2{gap:.5rem}.gap-3{gap:.75rem}.space-y-3>:not([hidden])~:not([hidden]){--tw-space-y-reverse: 0;margin-top:calc(.75rem * calc(1 - var(--tw-space-y-reverse)));margin-bottom:calc(.75rem * var(--tw-space-y-reverse))}.space-y-5>:not([hidden])~:not([hidden]){--tw-space-y-reverse: 0;margin-top:calc(1.25rem * calc(1 - var(--tw-space-y-reverse)));margin-bottom:calc(1.25rem * var(--tw-space-y-reverse))}.rounded-lg{border-radius:.5rem}.rounded-sm{border-radius:.125rem}.rounded-xl{border-radius:.75rem}.border{border-width:1px}.border-b{border-bottom-width:1px}.border-moli-border{--tw-border-opacity: 1;border-color:rgb(42 49 61 / var(--tw-border-opacity, 1))}.bg-moli-bg{--tw-bg-opacity: 1;background-color:rgb(15 17 21 / var(--tw-bg-opacity, 1))}.bg-moli-surface{--tw-bg-opacity: 1;background-color:rgb(23 26 33 / var(--tw-bg-opacity, 1))}.bg-moli-surface2{--tw-bg-opacity: 1;background-color:rgb(31 36 46 / var(--tw-bg-opacity, 1))}.p-2{padding:.5rem}.p-3\\.5{padding:.875rem}.p-4{padding:1rem}.px-4{padding-left:1rem;padding-right:1rem}.py-2\\.5{padding-top:.625rem;padding-bottom:.625rem}.py-3{padding-top:.75rem;padding-bottom:.75rem}.py-6{padding-top:1.5rem;padding-bottom:1.5rem}.text-\\[10px\\]{font-size:10px}.text-\\[12px\\]{font-size:12px}.text-\\[13px\\]{font-size:13px}.text-\\[14px\\]{font-size:14px}.text-\\[15px\\]{font-size:15px}.text-sm{font-size:.875rem;line-height:1.25rem}.text-xl{font-size:1.25rem;line-height:1.75rem}.text-xs{font-size:.75rem;line-height:1rem}.font-medium{font-weight:500}.leading-tight{line-height:1.25}.text-moli-muted{--tw-text-opacity: 1;color:rgb(154 163 178 / var(--tw-text-opacity, 1))}.text-moli-muted\\/70{color:#9aa3b2b3}.text-moli-text{--tw-text-opacity: 1;color:rgb(230 233 239 / var(--tw-text-opacity, 1))}.shadow{--tw-shadow: 0 1px 3px 0 rgb(0 0 0 / .1), 0 1px 2px -1px rgb(0 0 0 / .1);--tw-shadow-colored: 0 1px 3px 0 var(--tw-shadow-color), 0 1px 2px -1px var(--tw-shadow-color);box-shadow:var(--tw-ring-offset-shadow, 0 0 #0000),var(--tw-ring-shadow, 0 0 #0000),var(--tw-shadow)}.filter{filter:var(--tw-blur) var(--tw-brightness) var(--tw-contrast) var(--tw-grayscale) var(--tw-hue-rotate) var(--tw-invert) var(--tw-saturate) var(--tw-sepia) var(--tw-drop-shadow)}@media (min-width: 640px){.sm\\:grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}}@media (min-width: 768px){.md\\:grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}}';
class kt extends HTMLElement {
  constructor() {
    super();
    X(this, "_hass", null);
    X(this, "mountPoint");
    const n = this.attachShadow({ mode: "open" }), o = document.createElement("style");
    o.textContent = yt, n.appendChild(o), this.mountPoint = document.createElement("div"), n.appendChild(this.mountPoint);
  }
  set hass(n) {
    this._hass = n, this.renderApp();
  }
  get hass() {
    return this._hass;
  }
  connectedCallback() {
    this.renderApp();
  }
  renderApp() {
    Qe(Ne(vt, { hass: this._hass ?? { states: {} } }), this.mountPoint);
  }
}
customElements.get("moli-panel") || customElements.define("moli-panel", kt);
