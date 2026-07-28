/* ============================================================
 * decision-tooltip.js — 결정 참조 호버 툴팁 (docsify 플러그인)
 * ------------------------------------------------------------
 * 문서 본문에 나타나는 결정 참조(D-07, D-11 #29, D-12 ⑩, D-13②,
 * #29, D-20260723-13 등)에 커서를 올리면 결정로그.md의 원문
 * (제목·결정 내용·상태)을 플로팅 박스로 보여준다.
 * 클릭하면 결정로그의 해당 위치로 이동한다.
 *
 * 원문 출처: 01_운영문서/결정로그.md (단일 원본, 페이지 로드 시 fetch)
 * → 결정로그를 수정하면 툴팁도 자동 갱신된다. 별도 빌드 없음.
 *
 * 해석 규칙
 *  - D-NN            → 결정로그 항목 D-YYYYMMDD-NN (단축번호)
 *  - D-NN #n         → D-11 항목별 상태표 등 하위 #표의 n행
 *  - D-NN ①~⑮      → 하위 원문자 표(D-12 종결표·D-13 세부) 또는
 *                       해당 항목 '결정 내용' 안의 원문자 세부항목
 *  - #n (단독)       → 체크리스트 항목: D-11 상태표 n행(+D-12 종결 병기)
 *  - D-YYYYMMDD-NN   → 결정로그 항목 직접 참조
 *  - 해석 불가(예: D-14) → 상세회의록 임시번호 가능성 안내(ID 대응표)
 * ============================================================ */
(function () {
  'use strict';

  var LOG_PATH = '01_운영문서/결정로그.md';
  var LOG_ROUTE = '#/01_운영문서/결정로그';
  var CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮';

  /* ---------- 유틸 ---------- */
  function circledToNum(ch) { return CIRCLED.indexOf(ch) + 1; }
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  /* 마크다운 표 셀 텍스트 → 평문 (강조·코드·링크 표기 제거) */
  function plain(s) {
    return String(s == null ? '' : s)
      .replace(/\*\*([^*]*)\*\*/g, '$1')
      .replace(/`([^`]*)`/g, '$1')
      .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
      .replace(/<br\s*\/?>/gi, ' ')
      .trim();
  }
  /* 상태 문자열 → 배지 분류 */
  function statusTag(s) {
    if (!s) return { label: '', cls: 'dt-none' };
    /* "잠정 → 확정 (D-12 ①)" 같은 승격 표기는 → 뒤 최종 상태 기준 */
    var lead = s.split('→').pop().trim();
    if (/^(혼합|항목별)/.test(lead)) return { label: '혼합', cls: 'dt-part' };
    if (/^(잠정|기본안)/.test(lead)) return { label: '잠정', cls: 'dt-warn' };
    if (/^미결/.test(lead)) return { label: '미결', cls: 'dt-open' };
    if (/^보류/.test(lead)) return { label: '보류', cls: 'dt-hold' };
    if (/확정/.test(lead)) {
      /* "확정"으로 시작하면 완전 확정, 수식어가 붙으면 부분(구조) 확정 */
      if (/^[\[\*\s]*확정/.test(lead)) return { label: '확정', cls: 'dt-ok' };
      return { label: '구조 확정', cls: 'dt-part' };
    }
    return { label: lead.slice(0, 12), cls: 'dt-none' };
  }

  /* ---------- 결정로그 파서 ---------- */
  /* 표 한 줄 "| a | b | c |" → ['a','b','c'] */
  function splitRow(line) {
    var t = line.trim();
    if (t[0] !== '|') return null;
    t = t.replace(/^\|/, '').replace(/\|\s*$/, '');
    return t.split('|').map(function (c) { return c.trim(); });
  }

  function parseLog(md) {
    var db = { entries: {}, byFull: {}, sub: {}, order: [] };
    var lines = md.split(/\r?\n/);

    var curEntry = null;   // 현재 ### D-YYYYMMDD-NN 절
    var curSub = null;     // 현재 #### 하위 표 { entry: 'D-11', kind: 'hash'|'circle' }
    var curCols = null;    // 현재 표의 열 수 (구분자 행 기준)

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (!/^\s*\|/.test(line)) curCols = null;

      var h3 = line.match(/^###\s+(D-(\d{8})-(\d{2}))\s*[—–-]+\s*(.*)$/);
      if (h3) {
        var shortKey = 'D-' + String(parseInt(h3[3], 10)).padStart(2, '0');
        curEntry = {
          fullId: h3[1], key: shortKey, title: plain(h3[4]),
          content: '', status: '', headingText: line.replace(/^###\s+/, '')
        };
        db.entries[shortKey] = curEntry;
        db.byFull[h3[1]] = curEntry;
        db.order.push(shortKey);
        curSub = null;
        continue;
      }
      if (/^##[^#]/.test(line)) { curEntry = null; curSub = null; continue; }

      var h4 = line.match(/^####\s+(.*)$/);
      if (h4) {
        curSub = null;
        var st = h4[1];
        var owner = st.match(/D-(\d{1,2})/);
        if (owner) {
          var oKey = 'D-' + String(parseInt(owner[1], 10)).padStart(2, '0');
          if (/#|상태표/.test(st) && !/[①-⑮]/.test(st)) curSub = { entry: oKey, kind: 'hash' };
          else curSub = { entry: oKey, kind: /상태표/.test(st) ? 'hash' : 'circle' };
          db.sub[oKey] = db.sub[oKey] || { hash: {}, circle: {}, heading: st };
        }
        continue;
      }

      var cells = splitRow(line);
      if (!cells || cells.length < 2) continue;
      if (cells.every(function (c) { return /^[-:\s]*$/.test(c); })) { curCols = cells.length; continue; }
      /* 셀 내용 속 파이프(예: |근사−KRX|/KRX)로 과분할된 행을 열 수 기준으로 재결합 */
      if (curCols && cells.length > curCols) {
        cells = cells.slice(0, curCols - 1).concat(cells.slice(curCols - 1).join('|'));
      }

      /* 하위 표 행 */
      if (curSub && db.sub[curSub.entry]) {
        var store = db.sub[curSub.entry];
        var first = cells[0];
        var mNum = first.match(/^(\d{1,2})$/);
        var mCir = first.match(/^([①-⑮])\s*(.*)$/);
        if (mNum) {
          store.hash[parseInt(mNum[1], 10)] = {
            label: '#' + mNum[1],
            text: plain(cells[1] || ''),
            status: plain(cells[2] || '')
          };
          continue;
        }
        if (mCir) {
          var rest = mCir[2] || '';
          var hashRef = rest.match(/#(\d{1,2})/);
          store.circle[circledToNum(mCir[1])] = {
            label: mCir[1] + (rest ? ' ' + rest : ''),
            text: plain(cells[1] || ''),
            status: plain(cells[2] || ''),
            hashNum: hashRef ? parseInt(hashRef[1], 10) : null
          };
          continue;
        }
      }

      /* 본 항목 필드 표 행 */
      if (curEntry) {
        var field = cells[0];
        if (field === '결정 내용') curEntry.content = plain(cells.slice(1).join(' '));
        else if (field === '상태') curEntry.status = plain(cells.slice(1).join(' '));
      }
    }
    return db;
  }

  /* '결정 내용' 문자열에서 원문자 세부항목 추출 (예: D-04 ④, D-08 ①) */
  function inlineCircle(content, n) {
    if (!content) return null;
    var ch = CIRCLED[n - 1];
    if (!ch || content.indexOf(ch) < 0) return null;
    var parts = content.split(/(?=[①-⑮])/);
    for (var i = 0; i < parts.length; i++) {
      if (parts[i].charAt(0) === ch) return parts[i].trim();
    }
    return null;
  }

  /* ---------- 참조 스캐너 ---------- */
  /* 순서 중요: 전체 ID → D-NN(+꼬리) → #n 단독 */
  var REF_RE = new RegExp(
    'D-\\d{8}-\\d{2}' +
    '|D-\\d{1,2}(?!\\d)' +
      '(?:\\s?#\\d{1,2}(?:\\s?[·,]\\s?#?\\d{1,2})*' +
      '|\\s?[' + CIRCLED + ']+)?' +
    '|#\\d{1,2}(?![0-9A-Za-z])', 'g');

  /* 참조 문자열 → 해석 결과 배열
     [{key, sub, title, body, status, fullId, jump, unresolved}] */
  function resolveRef(text, db) {
    var out = [];

    var full = text.match(/^D-(\d{8})-(\d{2})$/);
    if (full) {
      var e0 = db.byFull[text];
      if (e0) out.push(entryItem(e0, text));
      else out.push(unresolvedItem(text));
      return out;
    }

    var m = text.match(new RegExp('^D-(\\d{1,2})\\s?(.*)$'));
    if (m) {
      var key = 'D-' + String(parseInt(m[1], 10)).padStart(2, '0');
      var entry = db.entries[key];
      var tail = m[2] || '';
      if (!entry) { out.push(unresolvedItem(text)); return out; }

      if (!tail) { out.push(entryItem(entry, text)); return out; }

      /* #n (복수 허용) */
      var hashNums = tail.match(/\d{1,2}/g);
      if (tail.indexOf('#') === 0 && hashNums) {
        hashNums.forEach(function (nStr) {
          var n = parseInt(nStr, 10);
          var row = db.sub[key] && db.sub[key].hash[n];
          if (row) out.push(rowItem(entry, key + ' #' + n, row, { hashOf: key, hashNum: n }));
          else {
            var seg = inlineCircle(entry.content, n);
            out.push(seg ? segItem(entry, key + ' #' + n, seg) : unresolvedItem(key + ' #' + n));
          }
        });
        return out;
      }

      /* 원문자 (복수 허용: ⑤⑥) */
      var circles = tail.match(new RegExp('[' + CIRCLED + ']', 'g'));
      if (circles) {
        circles.forEach(function (ch) {
          var n = circledToNum(ch);
          var row = db.sub[key] && db.sub[key].circle[n];
          if (row) out.push(rowItem(entry, key + ' ' + ch, row, { circleOf: key, circleNum: n }));
          else {
            var seg = inlineCircle(entry.content, n);
            out.push(seg ? segItem(entry, key + ' ' + ch, seg) : entryItem(entry, key + ' ' + ch));
          }
        });
        return out;
      }
      out.push(entryItem(entry, text));
      return out;
    }

    /* #n 단독 → D-11 상태표 (+ D-12 종결 병기) */
    var hm = text.match(/^#(\d{1,2})$/);
    if (hm) {
      var n2 = parseInt(hm[1], 10);
      var d11 = db.entries['D-11'];
      var row11 = db.sub['D-11'] && db.sub['D-11'].hash[n2];
      if (row11 && d11) {
        var item = rowItem(d11, 'D-11 #' + n2, row11, { hashOf: 'D-11', hashNum: n2 });
        item.refLabel = text;
        out.push(item);
        /* D-12 종결표에서 같은 #n을 다루는 행 병기 */
        var c12 = db.sub['D-12'] && db.sub['D-12'].circle;
        if (c12) {
          for (var k in c12) {
            if (c12[k].hashNum === n2) {
              var e12 = db.entries['D-12'];
              var it2 = rowItem(e12, 'D-12 ' + CIRCLED[k - 1] + ' (종결)', c12[k],
                { circleOf: 'D-12', circleNum: parseInt(k, 10) });
              out.push(it2);
              break;
            }
          }
        }
        return out;
      }
      return [];   /* 표에 없는 #n → 장식하지 않음 (오탐 방지) */
    }
    return out;
  }

  function entryItem(entry, refLabel) {
    return {
      refLabel: refLabel, fullId: entry.fullId, title: entry.title,
      body: entry.content, status: entry.status,
      jump: { fullId: entry.fullId }
    };
  }
  function rowItem(entry, refLabel, row, jumpExtra) {
    var j = { fullId: entry.fullId };
    for (var k in jumpExtra) j[k] = jumpExtra[k];
    return {
      refLabel: refLabel, fullId: entry.fullId,
      title: entry.title + (row.label ? ' — ' + row.label : ''),
      body: row.text, status: row.status || entry.status, jump: j
    };
  }
  function segItem(entry, refLabel, seg) {
    return {
      refLabel: refLabel, fullId: entry.fullId, title: entry.title,
      body: seg, status: entry.status, jump: { fullId: entry.fullId }
    };
  }
  function unresolvedItem(refLabel) {
    return {
      refLabel: refLabel, unresolved: true,
      title: '결정로그에서 찾을 수 없는 번호',
      body: '상세회의록의 임시번호(D-01~D-14)이거나 룰북 구버전 번호(M-01~M-08)일 수 있습니다. ' +
            '결정로그 말미의 "ID 대응표"에서 본 로그 번호를 확인하세요.',
      status: '', jump: { anchorText: 'ID 대응표' }
    };
  }

  /* Node 검증용 내보내기 */
  var core = {
    parseLog: parseLog, resolveRef: resolveRef, REF_RE: REF_RE,
    CIRCLED: CIRCLED, plain: plain, statusTag: statusTag
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = core;
  if (typeof window === 'undefined') return;   /* 브라우저 아니면 종료 */
  window.__decisionTooltipCore = core;

  /* ============================================================
   * 이하 브라우저(docsify) 전용
   * ============================================================ */

  var CSS = '\n' +
    '.dt-ref{border-bottom:1px dashed #42b983;color:#2c8a60;cursor:help;' +
      'border-radius:2px;padding:0 1px;transition:background .12s}\n' +
    '.dt-ref:hover{background:rgba(66,185,131,.12)}\n' +
    '.dt-ref.dt-unknown{border-bottom-color:#c9a227;color:#9a7b1c}\n' +
    '.dt-ref.dt-unknown:hover{background:rgba(201,162,39,.12)}\n' +
    '#dt-box{position:fixed;z-index:9999;max-width:480px;min-width:260px;' +
      'background:#fff;border:1px solid #d8dee4;border-radius:8px;' +
      'box-shadow:0 6px 24px rgba(27,49,66,.18);padding:0;font-size:13px;' +
      'line-height:1.55;color:#2c3e50;display:none}\n' +
    '#dt-box.dt-show{display:block}\n' +
    '#dt-box .dt-item{padding:10px 14px}\n' +
    '#dt-box .dt-item+.dt-item{border-top:1px solid #eef1f4}\n' +
    '#dt-box .dt-head{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:4px}\n' +
    '#dt-box .dt-id{font-weight:700;color:#2c8a60;font-size:12px;white-space:nowrap}\n' +
    '#dt-box .dt-title{font-weight:600}\n' +
    '#dt-box .dt-badge{font-size:11px;padding:1px 7px;border-radius:9px;white-space:nowrap}\n' +
    '#dt-box .dt-ok{background:#e2f5ea;color:#1d7a46}\n' +
    '#dt-box .dt-part{background:#e3eefc;color:#1e5fa8}\n' +
    '#dt-box .dt-warn{background:#fdf3d7;color:#8a6d1a}\n' +
    '#dt-box .dt-open{background:#fde3e3;color:#b23b3b}\n' +
    '#dt-box .dt-hold{background:#ececec;color:#666}\n' +
    '#dt-box .dt-none{background:#f1f3f5;color:#555}\n' +
    '#dt-box .dt-body{max-height:190px;overflow:auto;color:#3b4a58;white-space:pre-line}\n' +
    '#dt-box .dt-foot{border-top:1px solid #eef1f4;padding:6px 14px;font-size:11px;color:#8a97a3}\n' +
    '#dt-box .dt-warnnote{padding:6px 14px 0;font-size:11px;color:#9a7b1c}\n' +
    'tr.dt-flash,h3.dt-flash,h4.dt-flash{animation:dtflash 2.4s ease-out}\n' +
    '@keyframes dtflash{0%{background:#fff3bf}70%{background:#fff3bf}100%{background:transparent}}\n';

  var db = null, dbErr = null, box = null, hideTimer = null, showTimer = null;
  var pendingJump = null;

  function ensureCss() {
    if (document.getElementById('dt-style')) return;
    var st = document.createElement('style');
    st.id = 'dt-style'; st.textContent = CSS;
    document.head.appendChild(st);
  }
  function ensureBox() {
    if (box) return box;
    box = document.createElement('div');
    box.id = 'dt-box';
    box.addEventListener('mouseenter', function () { clearTimeout(hideTimer); });
    box.addEventListener('mouseleave', scheduleHide);
    document.body.appendChild(box);
    return box;
  }
  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function () { box && box.classList.remove('dt-show'); }, 220);
  }

  var logPromise = null;
  function loadLog() {
    if (logPromise) return logPromise;
    var base = (window.$docsify && window.$docsify.basePath) || '';
    logPromise = fetch(base + encodeURI(LOG_PATH)).then(function (r) {
      if (!r.ok) throw new Error('결정로그 fetch 실패: ' + r.status);
      return r.text();
    }).then(function (md) { db = parseLog(md); })
      .catch(function (e) { dbErr = e; console.warn('[decision-tooltip]', e); });
    return logPromise;
  }

  function isMeetingDoc() {
    var h = decodeURIComponent(location.hash || '');
    return h.indexOf('02_회의기록') >= 0;
  }

  function renderBox(items, warnNote) {
    var html = '';
    if (warnNote) html += '<div class="dt-warnnote">※ 회의기록의 D-번호는 상세회의록 임시번호일 수 있습니다 (결정로그 ID 대응표 참조)</div>';
    items.slice(0, 4).forEach(function (it) {
      var tag = statusTag(it.status);
      html += '<div class="dt-item">' +
        '<div class="dt-head">' +
          '<span class="dt-id">' + esc(it.unresolved ? it.refLabel : (it.fullId || '')) + '</span>' +
          '<span class="dt-title">' + esc(it.title) + '</span>' +
          (tag.label ? '<span class="dt-badge ' + tag.cls + '">' + esc(tag.label) + '</span>' : '') +
        '</div>' +
        '<div class="dt-body">' + esc(it.body) + '</div>' +
      '</div>';
    });
    if (items.length > 4) html += '<div class="dt-foot">… 외 ' + (items.length - 4) + '건</div>';
    html += '<div class="dt-foot">클릭하면 결정로그 해당 위치로 이동합니다</div>';
    ensureBox().innerHTML = html;
  }

  function positionBox(target) {
    var r = target.getBoundingClientRect();
    var b = ensureBox();
    b.style.left = '0px'; b.style.top = '0px';
    b.classList.add('dt-show');
    var bw = b.offsetWidth, bh = b.offsetHeight;
    var x = Math.min(Math.max(8, r.left), window.innerWidth - bw - 8);
    var y = r.bottom + 8;
    if (y + bh > window.innerHeight - 8) y = Math.max(8, r.top - bh - 8);
    b.style.left = x + 'px'; b.style.top = y + 'px';
  }

  function attach(span, items) {
    span.addEventListener('mouseenter', function () {
      clearTimeout(hideTimer); clearTimeout(showTimer);
      showTimer = setTimeout(function () {
        renderBox(items, isMeetingDoc());
        positionBox(span);
      }, 120);
    });
    span.addEventListener('mouseleave', function () {
      clearTimeout(showTimer); scheduleHide();
    });
    span.addEventListener('click', function (ev) {
      ev.preventDefault(); ev.stopPropagation();
      var jump = items[0] && items[0].jump;
      if (!jump) return;
      pendingJump = jump;
      box && box.classList.remove('dt-show');
      if (decodeURIComponent(location.hash).indexOf('01_운영문서/결정로그') >= 0) doJump();
      else location.hash = LOG_ROUTE;
    });
  }

  function doJump() {
    if (!pendingJump) return;
    var jump = pendingJump; pendingJump = null;
    var main = document.getElementById('main');
    if (!main) return;
    var target = null;

    if (jump.anchorText) {
      target = findHeading(main, jump.anchorText);
    } else if (jump.hashOf || jump.circleOf) {
      target = findSubRow(main, jump);
    }
    if (!target && jump.fullId) target = findHeading(main, jump.fullId);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      target.classList.remove('dt-flash');
      void target.offsetWidth;
      target.classList.add('dt-flash');
    }
  }
  function findHeading(main, text) {
    var hs = main.querySelectorAll('h2,h3,h4');
    for (var i = 0; i < hs.length; i++)
      if (hs[i].textContent.indexOf(text) >= 0) return hs[i];
    return null;
  }
  function findSubRow(main, jump) {
    var owner = jump.hashOf || jump.circleOf;
    var hs = main.querySelectorAll('h4');
    for (var i = 0; i < hs.length; i++) {
      if (hs[i].textContent.indexOf(owner) < 0) continue;
      var el = hs[i].nextElementSibling;
      while (el && el.tagName !== 'H2' && el.tagName !== 'H3' && el.tagName !== 'H4') {
        if (el.tagName === 'TABLE') {
          var rows = el.querySelectorAll('tbody tr');
          for (var r = 0; r < rows.length; r++) {
            var c0 = (rows[r].cells[0] || {}).textContent || '';
            c0 = c0.trim();
            if (jump.hashOf && c0 === String(jump.hashNum)) return rows[r];
            if (jump.circleOf && c0.charAt(0) === CIRCLED[jump.circleNum - 1]) return rows[r];
          }
        }
        el = el.nextElementSibling;
      }
    }
    return null;
  }

  /* 본문 텍스트 노드 스캔 → 참조를 span으로 치환 */
  var SKIP = { A: 1, CODE: 1, PRE: 1, SCRIPT: 1, STYLE: 1, TEXTAREA: 1, BUTTON: 1 };
  function decorate(root) {
    if (!db) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        var p = node.parentElement;
        while (p && p !== root) {
          if (SKIP[p.tagName] || p.classList.contains('dt-ref')) return NodeFilter.FILTER_REJECT;
          p = p.parentElement;
        }
        return /D-\d|#\d/.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);

    nodes.forEach(function (node) {
      var text = node.nodeValue;
      REF_RE.lastIndex = 0;
      var m, last = 0, frag = null;
      while ((m = REF_RE.exec(text)) !== null) {
        var items = resolveRef(m[0], db);
        if (!items.length) continue;
        if (!frag) frag = document.createDocumentFragment();
        if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        var span = document.createElement('span');
        span.className = 'dt-ref' + (items[0].unresolved ? ' dt-unknown' : '');
        span.textContent = m[0];
        attach(span, items);
        frag.appendChild(span);
        last = m.index + m[0].length;
      }
      if (frag) {
        if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
        node.parentNode.replaceChild(frag, node);
      }
    });
  }

  /* ---------- docsify 플러그인 등록 ---------- */
  function plugin(hook) {
    hook.mounted(function () { ensureCss(); loadLog(); });
    hook.doneEach(function () {
      ensureCss();
      var main = document.getElementById('main');
      if (!main) return;
      var run = function () { decorate(main); doJump(); };
      if (db || dbErr) run();
      else loadLog().then(run);
      document.addEventListener('scroll', function () {
        box && box.classList.remove('dt-show');
      }, { passive: true, once: true });
    });
  }
  window.$docsify = window.$docsify || {};
  window.$docsify.plugins = [].concat(plugin, window.$docsify.plugins || []);
})();
