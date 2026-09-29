// SPARC Studio page behavior: modals, confirmations, edit toggles, and
// "click a code, see the proof" evidence highlighting. No dependencies.
(function () {
  "use strict";

  // Open and close native <dialog> modals.
  document.addEventListener("click", function (event) {
    var opener = event.target.closest("[data-open-dialog]");
    if (opener) {
      var dialog = document.getElementById(opener.dataset.openDialog);
      if (dialog) { dialog.showModal(); }
      return;
    }
    var closer = event.target.closest("[data-close-dialog]");
    if (closer) { closer.closest("dialog").close(); }
  });

  // Print buttons (lesson view).
  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-print]")) { window.print(); }
  });

  // Ask before destructive form submits.
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
      event.preventDefault();
    }
  });

  // Swap a read view for its edit form (and back).
  document.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-toggle-edit]");
    if (!toggle) { return; }
    var root = toggle.closest("[data-editable]");
    var view = root.querySelector("[data-view]");
    var form = root.querySelector("[data-form]");
    var editing = form.hidden;
    form.hidden = !editing;
    view.hidden = editing;
    if (editing) {
      var field = form.querySelector("textarea, input:not([type=hidden])");
      if (field) { field.focus(); }
    }
  });

  // Evidence highlighting. Passages and items carry data-codes="S6E4.b ...";
  // rail cards carry data-standard and, when the evidence is elsewhere,
  // data-evidence-href pointing at the studio page that holds it.
  function marksFor(code) {
    return document.querySelectorAll('[data-codes~="' + code.replace(/"/g, "") + '"]');
  }

  function clearHighlights() {
    document.querySelectorAll(".is-lit").forEach(function (el) { el.classList.remove("is-lit"); });
    document.querySelectorAll(".std-card.is-active").forEach(function (card) {
      card.classList.remove("is-active");
      var button = card.querySelector("[data-highlight]");
      if (button) { button.setAttribute("aria-pressed", "false"); }
    });
  }

  function highlight(code) {
    var marks = marksFor(code);
    clearHighlights();
    if (!marks.length) { return false; }
    marks.forEach(function (el) { el.classList.add("is-lit"); });
    var card = document.querySelector('.std-card[data-standard="' + code + '"]');
    if (card) {
      card.classList.add("is-active");
      var button = card.querySelector("[data-highlight]");
      if (button) { button.setAttribute("aria-pressed", "true"); }
    }
    marks[0].scrollIntoView({ behavior: "smooth", block: "center" });
    return true;
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-highlight]");
    if (!button) { return; }
    var code = button.dataset.highlight;
    var card = button.closest(".std-card");
    if (card && card.classList.contains("is-active")) {
      clearHighlights();
      history.replaceState(null, "", location.pathname + location.search);
      return;
    }
    if (highlight(code)) {
      history.replaceState(null, "", "#" + encodeURIComponent(code));
    } else if (button.dataset.evidenceHref) {
      window.location.href = button.dataset.evidenceHref;
    }
  });

  // Arriving with #S6E4.b (from a standard's detail page) lights that code.
  if (location.hash.length > 1) {
    highlight(decodeURIComponent(location.hash.slice(1)));
  }
})();
