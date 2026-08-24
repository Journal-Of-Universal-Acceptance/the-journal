// -------------------------
// DARK MODE
// -------------------------

const themeToggle =
  document.getElementById("themeToggle");

const savedTheme =
  localStorage.getItem("jua-theme");

if (savedTheme === "dark") {
  document.body.classList.add("dark");
}

themeToggle.addEventListener("click", () => {

  document.body.classList.toggle("dark");

  const isDark =
    document.body.classList.contains("dark");

  localStorage.setItem(
    "jua-theme",
    isDark ? "dark" : "light"
  );

});


// -------------------------
// ARTICLE SEARCH
// -------------------------

const searchInput =
  document.getElementById("searchInput");

const articles =
  document.querySelectorAll(".article");

searchInput.addEventListener("input", () => {

  const query =
    searchInput.value.toLowerCase();

  articles.forEach(article => {

    const text =
      article.innerText.toLowerCase();

    const matches =
      text.includes(query);

    article.style.display =
      matches ? "block" : "none";

  });

});


// -------------------------
// SUBMISSION FORM
// -------------------------

const form =
  document.getElementById("submissionForm");

const modal =
  document.getElementById("modal");

const acceptanceMessage =
  document.getElementById("acceptanceMessage");

const closeModal =
  document.getElementById("closeModal");

const modalCloseButton =
  document.getElementById("modalCloseButton");


form.addEventListener("submit", event => {

  event.preventDefault();

  const name =
    document.getElementById("name").value;

  const title =
    document.getElementById("title").value;

  acceptanceMessage.textContent =
    `${name}, your submission "${title}" has been accepted without reservation, hesitation, or actual review.`;

  modal.classList.add("active");

  modal.setAttribute(
    "aria-hidden",
    "false"
  );

  form.reset();

});


// -------------------------
// CLOSE MODAL
// -------------------------

function hideModal() {

  modal.classList.remove("active");

  modal.setAttribute(
    "aria-hidden",
    "true"
  );

}


closeModal.addEventListener(
  "click",
  hideModal
);

modalCloseButton.addEventListener(
  "click",
  hideModal
);


modal.addEventListener(
  "click",
  event => {

    if (event.target === modal) {
      hideModal();
    }

  }
);


// Escape key

document.addEventListener(
  "keydown",
  event => {

    if (
      event.key === "Escape" &&
      modal.classList.contains("active")
    ) {
      hideModal();
    }

  }
);
