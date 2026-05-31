const toast = document.querySelector('#toast');
const copyButtons = document.querySelectorAll('.copy-command');
const commandSearch = document.querySelector('#commandSearch');
const commandCards = document.querySelectorAll('#commandGrid article');
const navLinks = document.querySelectorAll('.nav-list a');

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  window.setTimeout(() => toast.classList.remove('show'), 1800);
}

async function copyCommand(command) {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(command);
  }
  showToast(`Copied: ${command}`);
}

copyButtons.forEach((button) => {
  button.addEventListener('click', () => copyCommand(button.dataset.command));
});

commandSearch.addEventListener('input', (event) => {
  const query = event.target.value.trim().toLowerCase();

  commandCards.forEach((card) => {
    const text = `${card.textContent} ${card.dataset.keywords}`.toLowerCase();
    card.classList.toggle('hidden', query && !text.includes(query));
  });
});

const sections = [...navLinks]
  .map((link) => document.querySelector(link.getAttribute('href')))
  .filter(Boolean);

const observer = new IntersectionObserver(
  (entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

    if (!visible) return;

    navLinks.forEach((link) => {
      link.classList.toggle('active', link.getAttribute('href') === `#${visible.target.id}`);
    });
  },
  { rootMargin: '-25% 0px -60% 0px', threshold: [0.15, 0.3, 0.6] },
);

sections.forEach((section) => observer.observe(section));
