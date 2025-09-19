document.addEventListener('DOMContentLoaded', function(){
  const btn = document.getElementById('mobile-toggle');
  const menu = document.getElementById('mobile-menu');
  if(btn && menu){
    btn.addEventListener('click', ()=>{menu.classList.toggle('hidden');});
  }
  
  // Testimonial carousel: initialize only for homepage carousel container
  const homeCarousel = document.getElementById('home-testimonials');
  const wrapper = homeCarousel ? homeCarousel.querySelector('.testimonials-wrapper') : null;
  if(wrapper){
    const track = wrapper.querySelector('.testimonial-track');
    const items = Array.from(track ? track.children : []);
    let interval = null;
    let index = 0;

    function visibleCount(){
      if(window.innerWidth >= 1024) return 3; // lg
      if(window.innerWidth >= 640) return 2; // sm/md
      return 1; // mobile
    }

    function slideTo(i){
      const per = visibleCount();
      const itemW = items[0] ? items[0].getBoundingClientRect().width : 0;
      const shift = i * (itemW + 16); // gap=4 (1rem) approximated to 16px
      if(track) track.style.transform = `translateX(-${shift}px)`;
    }

    function startSliding(){ stopSliding(); interval = setInterval(()=>{ index = (index + 1) % Math.max(1, items.length); slideTo(index); }, 3500); }
    function stopSliding(){ if(interval){ clearInterval(interval); interval = null; } }

    // Start sliding only if there are items
    if(items.length){ startSliding(); }

    // Pause on hover
    wrapper.addEventListener('mouseenter', stopSliding);
    wrapper.addEventListener('mouseleave', startSliding);

    // Recalculate on resize
    window.addEventListener('resize', ()=>{ slideTo(index); });
  }

  // Read more modal for testimonials
  const modal = document.getElementById('testimonial-modal');
  const modalContent = document.getElementById('modal-content');
  const modalClose = document.getElementById('modal-close');
  document.querySelectorAll('.read-more-btn').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const full = btn.getAttribute('data-full');
      const author = btn.getAttribute('data-author');
      modalContent.innerHTML = `<div class=\"italic text-gray-700\">"${full}"</div><div class=\"mt-3 text-sm font-semibold\">— ${author}</div>`;
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    });
  });
  if(modalClose) modalClose.addEventListener('click', ()=>{ modal.classList.add('hidden'); modal.classList.remove('flex'); });
  if(modal) modal.addEventListener('click', (e)=>{ if(e.target===modal){ modal.classList.add('hidden'); modal.classList.remove('flex'); } });
});
