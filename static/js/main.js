document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("search-form");
    if (!form) return;

    form.addEventListener("submit", function () {
        const btn = document.getElementById("search-btn");
        const spinner = document.getElementById("search-spinner");
        const text = btn.querySelector(".btn-text");
        btn.disabled = true;
        spinner.classList.remove("d-none");
        text.textContent = "Searching...";
    });
});
