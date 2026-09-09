var DATA = {};
try{ DATA = JSON.parse(document.getElementById("explainer-data").textContent); }
catch(e){ console.error("[explainer-data] JSON 파싱 실패", e); }

function get(path, atEl){
  var val = path.split(".").reduce(function(o, k){
    return (o && Object.prototype.hasOwnProperty.call(o, k)) ? o[k] : undefined;
  }, DATA);
  if (val === undefined){
    console.error("[get] 경로를 찾을 수 없음: " + path);
    if (atEl){
      var b = document.createElement("span");
      b.className = "data-badge";
      b.textContent = "[데이터 없음: " + path + "]";
      // SVG 안(예: <tspan>)에 append하면 XHTML <span>이 0×0으로 렌더링되어 보이지 않으므로,
      // SVG 바깥으로 앵커를 끌어올린다.
      var anchor = atEl.closest("svg") || atEl;
      anchor.after(b);
    }
  }
  return val;
}

// 숫자가 아닌 값(예: 문자열 "1840")이 조용히 포맷되는 것을 막는 공용 가드.
// 모든 숫자 포맷터가 render 전에 이 가드를 거친다.
function numOrErr(v, name, render){
  if (v == null) return "—";
  if (!(typeof v === "number" && isFinite(v))){
    console.error("[FMT] " + name + " 숫자가 아닌 입력: " + v);
    return "[숫자 아님: " + v + "]";
  }
  return render(v);
}
var FMT = {
  int: function(v){ return numOrErr(v, "int", function(v){ return new Intl.NumberFormat("ko-KR").format(Math.round(v)); }); },
  num1: function(v){ return numOrErr(v, "num1", function(v){ return new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v); }); },
  num2: function(v){ return numOrErr(v, "num2", function(v){ return new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v); }); },
  deg0: function(v){ return numOrErr(v, "deg0", function(v){ return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 }).format(Math.round(v)) + "°"; }); },
  pct1: function(v){
    return numOrErr(v, "pct1", function(v){
      if (v < 0 || v > 1){
        console.error("[FMT] pct1 입력 범위 초과(0~1 기대): " + v);
        return "[비율 범위 초과: " + v + "]";
      }
      return new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v * 100) + "%";
    });
  },
  pct0: function(v){
    return numOrErr(v, "pct0", function(v){
      if (v < 0 || v > 1){
        console.error("[FMT] pct0 입력 범위 초과(0~1 기대): " + v);
        return "[비율 범위 초과: " + v + "]";
      }
      return new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(v * 100) + "%";
    });
  }
};
function fmt(name, v){
  if (!Object.prototype.hasOwnProperty.call(FMT, name)){
    console.error("[FMT] 등록되지 않은 포맷: " + name);
    return "[포맷 없음: " + name + "]";
  }
  return FMT[name](v);
}

// 본문의 정적 숫자는 JS 없이도 살아남아야 하므로 텍스트를 덮어쓰지 않는다.
// 계산값과 다르면 경고 배지만 옆에 붙인다. fmt()가 반환하는 오류 문자열은 항상 "["로
// 시작하므로, 그 경우 문자열이 우연히 정적 텍스트와 같더라도 항상 배지를 붙인다.
function verifyNumbers(){
  document.querySelectorAll(".num[data-src]").forEach(function(el){
    var src = el.dataset.src, f = el.dataset.fmt;
    var expected = fmt(f, get(src, el));
    var actual = el.textContent.trim();
    var isError = /^\[/.test(expected);
    if (expected !== actual || isError){
      console.error("[검증 실패] " + src + ": 표시 \"" + actual + "\" / 계산 \"" + expected + "\"");
      var b = document.createElement("span");
      b.className = "verify-badge";
      b.textContent = "불일치: " + expected;
      // SVG 안(예: <tspan>)에 append하면 XHTML <span>이 0×0으로 렌더링되어 보이지 않으므로,
      // SVG 바깥으로 앵커를 끌어올린다.
      var anchor = el.closest("svg") || el;
      anchor.after(b);
    }
  });
}

function svgEl(tag, attrs){
  var el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (var k in attrs) el.setAttribute(k, attrs[k]);
  return el;
}

// 전역 툴팁: hover와 focus 모두에서 열리고 Escape로 닫힌다. 한 요소가 hover와 focus를
// 동시에 갖고 있을 수 있으므로(같은 요소를 focus한 채 hover) 소유자(tipOwner)마다
// {hover, focus} 두 모달리티 플래그를 따로 추적하고, 둘 다 꺼졌을 때만 닫는다.
// openTip이 소유자가 바뀔 때 이전 소유자의 aria-describedby를 반드시 지운 뒤 갈아치우므로
// "A focus → B hover"처럼 소유자가 넘어가도 stale aria-describedby가 남지 않는다.
var tip = document.getElementById("tip");
var tipOwner = null;
var tipModes = { hover: false, focus: false };
function openTip(el, mode){
  if (tipOwner !== el){
    if (tipOwner) tipOwner.removeAttribute("aria-describedby");
    tipOwner = el;
    tipModes = { hover: false, focus: false };
    el.setAttribute("aria-describedby", "tip");
  }
  tipModes[mode] = true;
  tip.textContent = el.dataset.tip;
  var r = el.getBoundingClientRect();
  tip.style.left = (window.scrollX + r.left) + "px";
  tip.style.top = (window.scrollY + r.bottom + 6) + "px";
  tip.hidden = false;
}
function closeTip(el, mode){
  if (tipOwner !== el) return;
  tipModes[mode] = false;
  if (!tipModes.hover && !tipModes.focus) hideTip();
}
function hideTip(){
  tip.hidden = true;
  if (tipOwner){
    tipOwner.removeAttribute("aria-describedby");
    tipOwner = null;
  }
  tipModes = { hover: false, focus: false };
}
function wireTip(el, text){
  el.dataset.tip = text;
  el.setAttribute("aria-label", text);
  el.addEventListener("mouseenter", function(){ openTip(el, "hover"); });
  el.addEventListener("mouseleave", function(){ closeTip(el, "hover"); });
  el.addEventListener("focus", function(){ openTip(el, "focus"); });
  el.addEventListener("blur", function(){ closeTip(el, "focus"); });
}
document.addEventListener("keydown", function(e){ if (e.key === "Escape") hideTip(); });

// 범용 가로 막대 렌더러 — EXPL과 공용 툴팁 클로저(tipOwner/hideTip)가 로드된 문서
// 안에서라면 어디서든 그대로 동작한다.
function renderBarsH(svgId, data, opts){
  opts = opts || {};
  var svg = document.getElementById(svgId);
  if (!svg || !data || !data.length) return;
  if (tipOwner && svg.contains(tipOwner)) hideTip();
  svg.innerHTML = "";
  var w = 640, barH = opts.barH || 26, gap = opts.gap || (opts.annotate ? 28 : 12), left = opts.left || 100, top = 8;
  svg.setAttribute("viewBox", "0 0 " + w + " " + (data.length * (barH + gap) + top));
  var max = Math.max.apply(null, data.map(function(d){ return d.value; }));
  data.forEach(function(d, i){
    var y = top + i * (barH + gap);
    var bw = (w - left - 60) * (d.value / max);
    var color = opts.colorFn ? opts.colorFn(d, i) : "var(--c1)";
    var g = EXPL.svgEl("g", {});
    if (opts.barId) g.id = opts.barId(d, i);
    svg.appendChild(g);
    var bar = EXPL.svgEl("rect", { x: left, y: y, width: bw, height: barH, rx: 3, fill: color, tabindex: "0", role: "img" });
    g.appendChild(bar);
    EXPL.wireTip(bar, d.label + ": " + EXPL.fmt(opts.fmt || "int", d.value));
    if (opts.onEnter) bar.addEventListener("mouseenter", function(){ opts.onEnter(d, i, bar); });
    if (opts.onFocus) bar.addEventListener("focus", function(){ opts.onFocus(d, i, bar); });
    if (opts.onLeave){
      bar.addEventListener("mouseleave", function(){ opts.onLeave(d, i, bar); });
      bar.addEventListener("blur", function(){ opts.onLeave(d, i, bar); });
    }
    var label = EXPL.svgEl("text", { x: left - 8, y: y + barH * 0.68, "text-anchor": "end", class: "chart-label" });
    label.textContent = d.label;
    g.appendChild(label);
    var val = EXPL.svgEl("text", { x: left + bw + 8, y: y + barH * 0.68, class: "chart-value num" });
    val.textContent = EXPL.fmt(opts.fmt || "int", d.value);
    g.appendChild(val);
    if (opts.annotate && d.note){
      var note = EXPL.svgEl("text", { x: left, y: y + barH + 14, class: "chart-note" });
      note.textContent = d.note;
      g.appendChild(note);
    }
  });
}

// 축 보조선 — <g class="axis">를 svg의 첫 자식으로 넣어 데이터 마크 아래에 깔고, 만든 <g>를 반환한다.
// 0과 yMax 사이를 yTicks(기본 3)등분한 값마다 가로선과 x0 왼쪽에 붙는 눈금값을 그린다.
// xLabels 배열을 주면 슬롯마다 가운데 정렬한 라벨을 축 아래에 붙인다.
function axes(svg, opts){
  var x0 = opts.x0, y0 = opts.y0, w = opts.w, h = opts.h, ticks = opts.yTicks || 3;
  var g = EXPL.svgEl("g", { class: "axis" });
  svg.insertBefore(g, svg.firstChild);
  for (var k = 1; k <= ticks; k++){
    var y = y0 + h * (1 - k / ticks);
    g.appendChild(EXPL.svgEl("line", { x1: x0, y1: y, x2: x0 + w, y2: y, stroke: "currentColor", opacity: ".25" }));
    var tick = EXPL.svgEl("text", { x: x0 - 6, y: y + 4, "text-anchor": "end", class: "chart-value num" });
    tick.textContent = EXPL.fmt("int", opts.yMax * k / ticks);
    g.appendChild(tick);
  }
  if (Array.isArray(opts.xLabels)) opts.xLabels.forEach(function(s, i){
    var numeric = /^[\d.,%°-]+$/.test(String(s));
    var lab = EXPL.svgEl("text", { x: x0 + (i + 0.5) * w / opts.xLabels.length, y: y0 + h + 14, "text-anchor": "middle", class: numeric ? "chart-value num" : "chart-label" });
    lab.textContent = s;
    g.appendChild(lab);
  });
  return g;
}

// 다른 문서로 레시피를 복사했을 때도 동작하도록 공용 유틸리티를 전역에 노출한다.
window.EXPL = Object.freeze({ get: get, fmt: fmt, svgEl: svgEl, wireTip: wireTip, verifyNumbers: verifyNumbers, renderBarsH: renderBarsH, axes: axes });
