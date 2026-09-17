document.getElementById("anio").textContent = new Date().getFullYear();

var boton = document.getElementById("toggleHabilidades");
var lista = document.getElementById("listaHabilidades");

console.log("Habilidades listadas:", lista.children.length);

boton.addEventListener("click", function () {
  lista.classList.toggle("oculto");
});

