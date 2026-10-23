document.documentElement.dataset.js = "ready";

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
