---
title: Graph Network Visualization
layout: page
permalink: /graph-network-words-works.html
---

## Lexical Network Visualization

This page presents an interactive network visualization of the Bajubá lexicon and its connections to cultural productions catalogued in the digital archive. Each node represents either a lexical item or a cultural production; the links indicate which terms appear in each work. Click on any node to explore its connections and be redirected to the corresponding entry in the archive.

<div class="responsive-network-iframe">
  <iframe src="{{ site.baseurl }}/assets/network_graph_words_work_layout.html" 
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
