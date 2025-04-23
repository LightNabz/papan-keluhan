function toggleMenu() {
    const navLinks = document.getElementById('nav-links');
    const hamburger = document.querySelector('.hamburger');
    navLinks.classList.toggle('active');
    hamburger.classList.toggle('active');
}

/* // Sync repo dari fork orang
const GITHUB_USERNAME = "LightNabz"; 

async function fetchGitHubRepos() {
    const reposContainer = document.getElementById("repos-container");
    reposContainer.innerHTML = "<p>Loading repositories...</p>";

    try {
        const response = await fetch(`https://api.github.com/users/${GITHUB_USERNAME}/repos`);
        const repos = await response.json();

        reposContainer.innerHTML = "";

        repos.forEach(repo => {
            const repoBox = document.createElement("div");
            repoBox.className = "repo-box";

            repoBox.innerHTML = `
                <h3>${repo.name}</h3>
                <p>${repo.description || "No description available"}</p>
                <a href="${repo.html_url}" target="_blank">View Repository</a>
            `;

            reposContainer.appendChild(repoBox);
        });
    } catch (error) {
        reposContainer.innerHTML = "<p>Failed to load repositories. Please try again later.</p>";
        console.error("Error fetching GitHub repos:", error);
    }
}

fetchGitHubRepos(); */

window.addEventListener('scroll', function() {
    const nav = document.querySelector('nav');
    
    if (window.scrollY > 50) { 
        nav.classList.add('scrolled');
    } else {
        nav.classList.remove('scrolled');
    }
});

const toggleButton = document.getElementById('toggle-theme');
const themeLink = document.getElementById('theme-style');
const containers = document.querySelectorAll('.background-container');
const moonIcon = document.getElementById('moon-icon');
const sunIcon = document.getElementById('sun-icon');

let isDark = localStorage.getItem('theme') === 'dark' || !localStorage.getItem('theme');

// Your existing theme logic
function applyTheme() {
  if (isDark) {
    themeLink.href = 'assets/css/style.css';
    containers.forEach(container => {
      container.classList.remove('bg-[#f1f1f1]', 'bg-[#f2f2f2]');
      container.classList.add('bg-[#181825]', 'bg-[#1E1E2E]');
    });
  } else {
    themeLink.href = 'assets/css/stylel.css';
    containers.forEach(container => {
      container.classList.remove('bg-[#181825]', 'bg-[#1E1E2E]');
      container.classList.add('bg-[#f1f1f1]', 'bg-[#f2f2f2]');
    });
  }
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// New button state handler
function updateButtonState() {
  // Toggle icons
  moonIcon.classList.toggle('hidden', !isDark);
  sunIcon.classList.toggle('hidden', isDark);
  
  // Toggle dark class for styling
  document.documentElement.classList.toggle('dark', isDark);
  
  // Add animations
  const activeIcon = isDark ? moonIcon : sunIcon;
  activeIcon.animate([
    { transform: 'scale(1)', opacity: 1 },
    { transform: 'scale(0)', opacity: 0 },
    { transform: 'scale(1)', opacity: 1 }
  ], { duration: 300 });
}

toggleButton.addEventListener('click', () => {
  isDark = !isDark;
  applyTheme(); // Your existing theme logic
  updateButtonState(); // New button handling
});

// Initial setup
applyTheme();
updateButtonState();

const hero = document.querySelector('.hero');
const spotlight = document.createElement('div');
spotlight.classList.add('spotlight');
hero.appendChild(spotlight);

let mouseX = 0, mouseY = 0;
let spotlightX = 0, spotlightY = 0;

hero.addEventListener('mousemove', (e) => {
  const rect = hero.getBoundingClientRect();
  mouseX = e.clientX - rect.left;
  mouseY = e.clientY - rect.top;
  spotlight.style.opacity = 1;
});

hero.addEventListener('mouseleave', () => {
  spotlight.style.opacity = 0;
});

function animate() {
  // Smooth interpolation
  spotlightX += (mouseX - spotlightX) * 0.1;
  spotlightY += (mouseY - spotlightY) * 0.1;

  spotlight.style.left = `${spotlightX}px`;
  spotlight.style.top = `${spotlightY}px`;

  requestAnimationFrame(animate);
}

animate();