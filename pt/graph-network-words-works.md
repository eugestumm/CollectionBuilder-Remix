---
title: Gráfico de Rede por Obra
layout: page

---

## Visualização Léxica em Rede

Esta página apresenta uma visualização interativa em rede do léxico do Bajubá e suas conexões com produções culturais catalogadas no arquivo digital. Cada nó representa um item lexical ou uma produção cultural; as conexões indicam quais termos aparecem em cada obra. Clique em qualquer nó para explorar suas conexões e ser redirecionado à entrada correspondente no arquivo.

<div class="responsive-network-iframe">
  <iframe src="{{ site.baseurl }}/assets/network_graph_words_work_layout_portuguese.html" 
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
