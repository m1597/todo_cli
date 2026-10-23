// ===========================================================================
// 这个文件只在浏览器里运行，负责“让页面更好用”。
// 核心功能（增删改查）由服务器完成，这里只做确认弹窗、自动提交等小交互。
//
// 常用写法：
//   document.querySelector(...)      找页面上的第一个元素
//   document.querySelectorAll(...)   找所有匹配的元素，返回列表
//   element.addEventListener(...)    给元素绑定事件（点击、提交等）
// ===========================================================================

// 给 <html> 加一个标记，表示 JavaScript 已经加载成功。
document.documentElement.dataset.js = "ready";

// 操作成功的绿色提示，4 秒后淡出并从页面移除。
const flashMessage = document.querySelector(".flash");
if (flashMessage) {
  window.setTimeout(() => {
    flashMessage.classList.add("is-hiding");
    window.setTimeout(() => flashMessage.remove(), 350);
  }, 4000);
}

// 删除前弹窗确认；cancel 时阻止表单提交。
document.querySelectorAll(".delete-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("确定删除这条待办吗？")) {
      event.preventDefault();
    }
  });
});

// 清空已完成前也确认一次。
document.querySelectorAll(".clear-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("确定清空所有已完成的待办吗？")) {
      event.preventDefault();
    }
  });
});

// 筛选区的下拉框一改变，就自动提交整个筛选表单，不用再点“应用”。
document.querySelectorAll(".filter-form select").forEach((select) => {
  select.addEventListener("change", () => {
    select.form.requestSubmit();
  });
});
