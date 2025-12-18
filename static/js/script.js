// Mobile nav toggle
const navToggle = document.getElementById("navToggle");
const nav = document.getElementById("nav");

if (navToggle && nav) {
  navToggle.addEventListener("click", () => {
    nav.classList.toggle("open");
    navToggle.classList.toggle("open");
  });
}

// Theme toggle (light / dark switch on body)
const themeToggle = document.getElementById("themeToggle");
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("light-theme");
  });
}

// Scroll to top button
const scrollBtn = document.getElementById("scrollTop");
if (scrollBtn) {
  window.addEventListener("scroll", () => {
    if (window.scrollY > 200) {
      scrollBtn.classList.add("show");
    } else {
      scrollBtn.classList.remove("show");
    }
  });
  scrollBtn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

// Simple typewriter effect for role text
const roles = ["Website Developer", "Frontend Developer", "Python & Flask Developer"];
let roleIndex = 0;
let charIndex = 0;
const typeSpan = document.getElementById("typeRole");
const cursor = document.querySelector(".hero-cursor");

function typeRole() {
  if (!typeSpan) return;
  const current = roles[roleIndex];
  if (charIndex <= current.length) {
    typeSpan.textContent = current.substring(0, charIndex);
    charIndex++;
    setTimeout(typeRole, 120);
  } else {
    setTimeout(eraseRole, 1500);
  }
}

function eraseRole() {
  if (!typeSpan) return;
  const current = roles[roleIndex];
  if (charIndex >= 0) {
    typeSpan.textContent = current.substring(0, charIndex);
    charIndex--;
    setTimeout(eraseRole, 60);
  } else {
    roleIndex = (roleIndex + 1) % roles.length;
    setTimeout(typeRole, 300);
  }
}

if (typeSpan) {
  typeRole();
}

// Intersection observer for fade-in sections
const fadeEls = document.querySelectorAll(".fade-in");
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );

  fadeEls.forEach((el) => observer.observe(el));
}
