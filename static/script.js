document.addEventListener('DOMContentLoaded', function() {
    // -----------------------------
    // Search button functionality
    // -----------------------------
    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            const city = document.getElementById('city').value;
            const propertyType = document.getElementById('property-type').value;
            const price = document.getElementById('price').value;
            alert(`Searching for properties in ${city}, type: ${propertyType}, max price: ${price}`);
        });
    }

    // -----------------------------
    // Property card hover effects
    // -----------------------------
    document.querySelectorAll('.property-card').forEach(card => {
        card.addEventListener('mouseenter', () => card.style.transform = 'translateY(-10px)');
        card.addEventListener('mouseleave', () => card.style.transform = 'translateY(0)');
    });

    // -----------------------------
    // Form input visual feedback
    // -----------------------------
    document.querySelectorAll('.search-input input, .search-input select').forEach(input => {
        input.addEventListener('input', () => {
            input.style.borderColor = input.value.trim() !== '' ? '#26a269' : '#e0e0e0';
        });
    });

    // -----------------------------
    // Smooth scrolling
    // -----------------------------
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetElement = document.querySelector(this.getAttribute('href'));
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });

    // -----------------------------
    // Format property prices
    // -----------------------------
    document.querySelectorAll('.property-price').forEach(priceElement => {
        const formattedPrice = priceElement.textContent.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,');
        priceElement.textContent = formattedPrice;
    });

    // -----------------------------
    // Animate elements on view
    // -----------------------------
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) entry.target.classList.add('animate-in');
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.property-card, .cta-section, .hero').forEach(el => observer.observe(el));

    // -----------------------------
    // Auto-hide flash messages
    // -----------------------------
    document.querySelectorAll('.flash-message').forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => { message.remove(); }, 300);
        }, 5000);
    });

    document.querySelectorAll('.flash-close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            const message = closeBtn.parentElement;
            message.style.opacity = '0';
            setTimeout(() => { message.remove(); }, 300);
        });
    });

    // =============================
    // AI Price Prediction Feature
    // =============================
    const predictBtn = document.getElementById("predict-btn");
    if (predictBtn) {
        predictBtn.addEventListener("click", async function () {
            // Helper to safely get input values by id
            const getVal = (id) => {
                const el = document.getElementById(id);
                return el ? el.value : '';
            };

            // Grab the ML input values (use IDs to match template)
            const overall_qual = getVal('overall_qual');
            const gr_liv_area = getVal('gr_liv_area');
            const total_bath = getVal('total_bath');
            const total_sf = getVal('total_sf');
            const house_age = getVal('house_age');
            const remodel_age = getVal('remodel_age');

            // Validate inputs
            if (!overall_qual || !gr_liv_area || !total_bath || !total_sf || !house_age || !remodel_age) {
                alert("Please fill all AI prediction fields first.");
                return;
            }

            try {
                const response = await fetch("/predict_price", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        overall_qual,
                        gr_liv_area,
                        total_bath,
                        total_sf,
                        house_age,
                        remodel_age
                    })
                });

                if (!response.ok) {
                    const txt = await response.text().catch(() => '<no body>');
                    const msg = `Prediction API returned ${response.status} ${response.statusText}: ${txt}`;
                    alert(msg);
                    console.error('Prediction API error:', response.status, response.statusText, txt);
                    return;
                }

                let data;
                try {
                    data = await response.json();
                } catch (parseErr) {
                    const txt = await response.text().catch(() => '<no body>');
                    alert('Failed to parse JSON from prediction API: ' + txt);
                    console.error('JSON parse error from prediction API:', parseErr, txt);
                    return;
                }

                if (data.predicted_price) {
                    // Show predicted price box
                    const box = document.getElementById("predicted-box");
                    if (box) {
                        box.style.display = "block";
                        box.textContent = "Predicted Price: € " + data.predicted_price;
                    }

                    // Fill the price input so user can modify it
                    const priceInput = document.getElementById("price");
                    if (priceInput) priceInput.value = data.predicted_price;
                } else {
                    alert("Prediction failed: " + (data.error || "Unknown error"));
                }
            } catch (err) {
                alert("Error contacting prediction API: " + (err && err.message ? err.message : err));
                console.error('Fetch error contacting prediction API:', err);
            }
        });
    }

    // -----------------------------
    // Dynamic Interior Images Inputs
    // -----------------------------
    const interiorContainer = document.getElementById('interior-container');
    const addMoreBtn = document.getElementById('add-more-btn');

    if (interiorContainer && addMoreBtn) {
        addMoreBtn.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.name = 'interior_images';
            input.accept = 'image/*';
            input.multiple = true;
            input.style.marginTop = '5px';
            interiorContainer.insertBefore(input, addMoreBtn);
        });
    }

       // -----------------------------
    // Contact Agent Button (only on house detail page)
    // -----------------------------
    const contactBtn = document.getElementById('contact-btn');
    if (contactBtn) {
        contactBtn.addEventListener('click', function() {
            const info = document.getElementById('contact-info');
            if (info.style.display === 'none' || info.style.display === '') {
                info.style.display = 'block';
                this.textContent = 'Hide Contact Info';
            } else {
                info.style.display = 'none';
                this.textContent = 'Contact Info';
            }
        });
    }

    // Dark mode toggle
    document.getElementById('theme-toggle')?.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isDark);
        
        const icon = document.querySelector('#theme-toggle i');
        icon.classList.toggle('fa-moon', !isDark);
        icon.classList.toggle('fa-sun', isDark);
    });

    // Load saved theme
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
        document.querySelector('#theme-toggle i')?.classList.replace('fa-moon', 'fa-sun');
    }
});
