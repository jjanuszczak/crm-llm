function replaceTarget(targetSelector, html, swapMode) {
  const target = document.querySelector(targetSelector);
  if (!target) return;
  if (swapMode === "outerHTML") {
    target.outerHTML = html;
    if (targetSelector === "#detail-drawer") {
      document.body.classList.add("drawer-open");
    }
    return;
  }
  target.innerHTML = html;
}

async function loadPartial(url, targetSelector, swapMode) {
  const response = await fetch(url, { headers: { "X-Requested-With": "fetch" } });
  const html = await response.text();
  replaceTarget(targetSelector, html, swapMode);
}

function setDrawerCollapsed(drawer, collapsed) {
  drawer.classList.toggle("is-collapsed", collapsed);
  document.body.classList.toggle("drawer-open", !collapsed);
}

function queryFromForm(form) {
  const params = new URLSearchParams();
  for (const element of form.elements) {
    if (!element.name || element.disabled) continue;
    if (element.type === "hidden" && form.querySelector(`input[type="checkbox"][name="${element.name}"]:checked`)) continue;
    if ((element.type === "checkbox" || element.type === "radio") && !element.checked) continue;
    params.append(element.name, element.value);
  }
  return params.toString();
}

document.addEventListener("change", (event) => {
  const form = event.target.closest("form[hx-get]");
  if (!form) return;
  const query = queryFromForm(form);
  const url = query ? `${form.getAttribute("hx-get")}?${query}` : form.getAttribute("hx-get");
  loadPartial(url, form.getAttribute("hx-target"), form.getAttribute("hx-swap") || "innerHTML");
});

document.addEventListener("click", (event) => {
  const drawerToggle = event.target.closest("[data-drawer-toggle]");
  if (drawerToggle) {
    const drawer = document.querySelector("#detail-drawer");
    if (!drawer) return;
    setDrawerCollapsed(drawer, !drawer.classList.contains("is-collapsed"));
    return;
  }

  const collapsedDrawer = event.target.closest("#detail-drawer.is-collapsed");
  if (collapsedDrawer) {
    setDrawerCollapsed(collapsedDrawer, false);
    return;
  }

  const trigger = event.target.closest("[hx-get]");
  if (!trigger || trigger.tagName === "FORM") return;
  loadPartial(trigger.getAttribute("hx-get"), trigger.getAttribute("hx-target"), trigger.getAttribute("hx-swap") || "innerHTML");
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const trigger = event.target.closest("[hx-get]");
  if (!trigger || trigger.tagName === "FORM") return;
  event.preventDefault();
  loadPartial(trigger.getAttribute("hx-get"), trigger.getAttribute("hx-target"), trigger.getAttribute("hx-swap") || "innerHTML");
});
