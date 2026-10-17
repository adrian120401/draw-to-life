() => {
  // UploadButton no expone capture. Ajustar solo su input nativo y conservar
  // el transporte y la validación de Gradio para ambos orígenes.
  const configure = () => {
    const button = document.getElementById('camera-upload');
    const input = button?.querySelector('input[type="file"]') || button?.previousElementSibling;
    if (input?.matches('input[type="file"]')) {
      if (input.getAttribute('capture') !== 'environment') input.setAttribute('capture', 'environment');
      if (input.accept !== 'image/*') input.accept = 'image/*';
    }
  };
  configure();
  const observer = new MutationObserver(configure);
  observer.observe(document.body, {childList: true, subtree: true});
  window.addEventListener('pagehide', () => observer.disconnect(), {once: true});
}
