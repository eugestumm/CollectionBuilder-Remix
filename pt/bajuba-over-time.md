---
title: Linha do Tempo - Registro de Palavras em Pajubá
layout: page

---

## Linha do Tempo: Registro de Palavras em Pajubá

Este gráfico mapeia **mais de 350 palavras do Pajubá** de acordo com o ano do primeiro registro conhecido.

Cada bolha é uma palavra. Sua posição horizontal indica quando foi registrada pela primeira vez. **As bolhas douradas** apareceram na grande mídia brasileira; **as bolhas azuis**, não.

Agrupamentos verticais densos indicam anos com muitas palavras documentadas. Use os filtros para mostrar ou ocultar cada grupo, ajuste o intervalo de anos para focar em um período e amplie para ler as palavras individualmente.

<div class="responsive-network-iframe">
  <iframe src="{{ site.baseurl }}/assets/visualization_pajuba_over_time_portuguese.html" 
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
