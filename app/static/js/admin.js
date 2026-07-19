(function () {
  const select = document.getElementById("type-select");
  const groups = document.querySelectorAll(".type-fields");

  function applyVisibility(type) {
    groups.forEach((group) => {
      group.classList.toggle("active", group.dataset.type === type);
    });
  }

  if (select) {
    applyVisibility(select.value);
    select.addEventListener("change", () => applyVisibility(select.value));
  } else {
    const hidden = document.querySelector('input[type="hidden"][name="type"]');
    if (hidden) applyVisibility(hidden.value);
  }
})();
