(function () {
  function aplicar() {
    var b = document.body;
    if (!b) return;
    var meta = document.querySelector('meta[name="am-classes"]');
    var lista = (meta && meta.getAttribute("content")) || window.__amClasses || "";
    lista.split(" ").forEach(function (c) {
      if (c) b.classList.add(c);
    });
    b.classList.add("am");

    // Tabela de baralhos (o Anki nem sempre dá um id a ela)
    var linha = document.querySelector("tr.deck");
    if (linha) {
      var tab = linha.closest("table");
      if (tab) tab.classList.add("am-decktable");
    }

    // Animação de entrada suave nas linhas
    var rows = document.querySelectorAll("tr.deck");
    rows.forEach(function (r, i) {
      r.style.animationDelay = Math.min(i * 22, 400) + "ms";
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", aplicar);
  } else {
    aplicar();
  }
})();
