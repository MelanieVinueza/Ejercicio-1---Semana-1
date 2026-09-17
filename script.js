document.getElementById("anio").textContent = new Date().getFullYear();

var boton = document.getElementById("toggleHabilidades");
var lista = document.getElementById("listaHabilidades");

boton.addEventListener("click", function () {
  var oculta = lista.classList.toggle("oculto");
  boton.setAttribute("aria-expanded", String(!oculta));
});

