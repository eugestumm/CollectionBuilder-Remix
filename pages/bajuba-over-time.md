---
title: Timeline - Documentating Lexicon in Bajubá Over Time
layout: page
permalink: /bajuba-over-time.html
---

# Pajubá — Documentation Over Time

This chart maps **over 350 words from Pajubá** by their year of first known documentation.

Each bubble is a word. Its horizontal position marks when it was first recorded. **Gold bubbles** appear in Brazilian mass media; **blue bubbles** do not.

Dense vertical clusters indicate years with many documented words. Use the filters to show or hide each group, adjust the year range to focus on a period, and zoom in to read individual words.

<div class="responsive-network-iframe">
  <iframe src="{{ site.baseurl }}/assets/visualization_pajuba_over_time.html" 
          allowfullscreen>
  </iframe>
</div>

<style>
.responsive-network-iframe {
  width: 100%;
  height: 800px; /* Much taller for desktop */
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  margin: 20px 0;
}

.responsive-network-iframe iframe {
  width: 100%;
  height: 100%;
  border: none;
  transform-origin: 0 0;
}

/* Tablet adjustments */
@media (max-width: 1024px) {
  .responsive-network-iframe {
    height: 700px;
  }
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .responsive-network-iframe {
    height: 80vh; /* Use viewport height on mobile */
    min-height: 500px;
    margin: 10px -15px; /* Extend to screen edges */
    border-radius: 0;
  }
  
  .responsive-network-iframe iframe {
    transform: scale(1.1); /* Slight scale for better readability */
    width: 90.9%;
    height: 90.9%;
  }
}

/* Small phones */
@media (max-width: 480px) {
  .responsive-network-iframe {
    height: 85vh;
    min-height: 450px;
  }
  
  .responsive-network-iframe iframe {
    transform: scale(1.2);
    width: 83.33%;
    height: 83.33%;
  }
}
</style>
