/*
 * 一覧ページの絞り込みと並び替え。
 *
 * バッジの情報は各 <li> の data 属性に埋め込んであるので、
 * 別途 JSON を読み込む必要はない。ビルド不要の素の JavaScript で動く。
 */
(function () {
  "use strict";

  var list = document.getElementById("badges");
  var controls = document.getElementById("controls");
  if (!list || !controls) {
    return;
  }

  var query = document.getElementById("q");
  var sort = document.getElementById("sort");
  var status = document.getElementById("status");
  var items = Array.prototype.slice.call(list.children);
  var total = items.length;

  // 日本語は文字コード順では読みの順にならないため、ロケールを指定して比較する。
  // それでも漢字は読み仮名まではたどれない点に注意（OBF に読み仮名の項目がない）。
  var collator = new Intl.Collator("ja");

  var comparators = {
    "name-asc": function (a, b) {
      return collator.compare(a.dataset.name, b.dataset.name);
    },
    "ctime-asc": function (a, b) {
      return Number(a.dataset.ctime) - Number(b.dataset.ctime);
    },
    "mtime-asc": function (a, b) {
      return Number(a.dataset.mtime) - Number(b.dataset.mtime);
    }
  };

  function comparatorFor(value) {
    var parts = value.split("-");
    var base = comparators[parts[0] + "-asc"] || comparators["name-asc"];
    if (parts[1] !== "desc") {
      return base;
    }
    return function (a, b) {
      // 同順位は名前の昇順で安定させる
      return -base(a, b) || collator.compare(a.dataset.name, b.dataset.name);
    };
  }

  function apply() {
    var keyword = query.value.trim().toLowerCase();
    var visible = 0;

    items.forEach(function (item) {
      var hit = keyword === "" || item.dataset.search.indexOf(keyword) !== -1;
      item.hidden = !hit;
      if (hit) {
        visible += 1;
      }
    });

    items
      .slice()
      .sort(comparatorFor(sort.value))
      .forEach(function (item) {
        list.appendChild(item);
      });

    if (keyword === "") {
      status.textContent = total + " 件";
    } else if (visible === 0) {
      status.textContent = "「" + query.value.trim() + "」に一致するバッジはありません。";
    } else {
      status.textContent = total + " 件中 " + visible + " 件を表示";
    }
  }

  // ここまで到達できた＝JavaScript が動く環境なので UI を見せる
  controls.hidden = false;
  status.hidden = false;
  controls.addEventListener("submit", function (event) {
    event.preventDefault();
  });
  query.addEventListener("input", apply);
  sort.addEventListener("change", apply);
  apply();
})();
