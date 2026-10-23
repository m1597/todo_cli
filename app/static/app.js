document.documentElement.dataset.js = "ready";

const flashMessage = document.querySelector(".flash");
if (flashMessage) {
  window.setTimeout(() => {
    flashMessage.classList.add("is-hiding");
    window.setTimeout(() => flashMessage.remove(), 350);
  }, 4000);
}

document.querySelectorAll(".delete-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("确定删除这条待办吗？")) {
      event.preventDefault();
    }
  });
});

document.querySelectorAll(".clear-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("确定清空所有已完成的待办吗？")) {
      event.preventDefault();
    }
  });
});

document.querySelectorAll(".filter-form select").forEach((select) => {
  select.addEventListener("change", () => {
    select.form.requestSubmit();
  });
});
