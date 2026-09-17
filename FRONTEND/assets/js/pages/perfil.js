import { userService } from "../api/user.service.js";

// Variables globales
let usuario = null;
let nombreOriginal = null;
let emailOriginal = null;
let telefonoOriginal = null;
let documentoOriginal = null;

// Referencias a elementos DOM
let contenedorNombre = null;
let contenedorEmail = null;
let contenedorTelefono = null;
let contenedorDocumento = null;
let contenedorRol = null;
let contenedorDescripcionRol = null;
let contenedorEstado = null;
let botonEditarPerfil = null;
let botonAceptar = null;
let botonCancelar = null;

async function init() {
  // Obtener usuario del localStorage
  usuario = JSON.parse(localStorage.getItem("user"));

  if (!usuario) {
    return;
  }

  // Obtener referencias a elementos DOM - ESPERAR a que el DOM esté listo
  await esperarDOM();

  contenedorNombre = document.getElementById("nombre");
  contenedorEmail = document.getElementById("email");
  contenedorTelefono = document.getElementById("telefono");
  contenedorDocumento = document.getElementById("documento");
  contenedorRol = document.getElementById("rol_usuario");
  contenedorDescripcionRol = document.getElementById("descripcion_rol_usuario");
  contenedorEstado = document.getElementById("estado_usuario");
  botonEditarPerfil = document.getElementById("boton-editar-perfil");
  botonAceptar = document.getElementById("boton-aceptar");
  botonCancelar = document.getElementById("boton-cancelar");

  // Verificar que todos los elementos existen
  if (!contenedorNombre || !contenedorEmail || !botonEditarPerfil) {
    // Reintentar después de un breve retraso (solo si seguimos en el perfil)
    if (window.currentPage === "perfil") setTimeout(init, 100);
    return;
  }

  // Inicializar valores
  actualizarValoresCampos();

  // Configurar event listeners
  configurarEventListeners();
}

// Función para esperar a que el DOM esté listo
function esperarDOM() {
  return new Promise((resolve) => {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", resolve);
    } else {
      resolve();
    }
  });
}

function actualizarValoresCampos() {
  if (!usuario) return;

  nombreOriginal = usuario.nombre;
  emailOriginal = usuario.email;
  telefonoOriginal = usuario.telefono;
  documentoOriginal = usuario.documento;

  // Asignar valores a los campos
  contenedorNombre.value = nombreOriginal || "";
  contenedorEmail.value = emailOriginal || "";
  contenedorTelefono.value = telefonoOriginal || "";
  contenedorDocumento.value = documentoOriginal || "";

  // Campos de solo lectura
  if (contenedorRol) contenedorRol.value = usuario.nombre_rol || "";
  if (contenedorDescripcionRol)
    contenedorDescripcionRol.value = usuario.descripcion_rol || "";
  if (contenedorEstado)
    contenedorEstado.value = usuario.estado ? "Activa" : "Desactivada";

  // Deshabilitar campos editables
  deshabilitarCampos();
}

function configurarEventListeners() {
  // Remover event listeners previos para evitar duplicación
  botonEditarPerfil.removeEventListener("click", habilitarEdicion);
  botonAceptar.removeEventListener("click", tomarEnviarDatos);
  botonCancelar.removeEventListener("click", cancelarEdicion);

  // Agregar nuevos event listeners
  botonEditarPerfil.addEventListener("click", habilitarEdicion);
  botonAceptar.addEventListener("click", tomarEnviarDatos);
  botonCancelar.addEventListener("click", cancelarEdicion);
}

function habilitarEdicion() {
  botonEditarPerfil.classList.add("d-none");
  botonAceptar.classList.remove("d-none");
  botonCancelar.classList.remove("d-none");

  contenedorNombre.removeAttribute("disabled");
  contenedorEmail.removeAttribute("disabled");
  contenedorTelefono.removeAttribute("disabled");
  contenedorDocumento.removeAttribute("disabled");
}

function deshabilitarCampos() {
  contenedorNombre.setAttribute("disabled", "");
  contenedorEmail.setAttribute("disabled", "");
  contenedorTelefono.setAttribute("disabled", "");
  contenedorDocumento.setAttribute("disabled", "");
}

function cancelarEdicion() {
  if (!nombreOriginal || !emailOriginal) {
    // Recargar valores desde localStorage si se perdieron
    usuario = JSON.parse(localStorage.getItem("user"));
    actualizarValoresCampos();
  } else {
    contenedorNombre.value = nombreOriginal;
    contenedorEmail.value = emailOriginal;
    contenedorTelefono.value = telefonoOriginal;
    contenedorDocumento.value = documentoOriginal;
  }

  deshabilitarCampos();
  botonEditarPerfil.classList.remove("d-none");
  botonAceptar.classList.add("d-none");
  botonCancelar.classList.add("d-none");
}

async function tomarEnviarDatos() {
  if (!usuario) return;

  let idUser = usuario.id_usuario;

  let nombreNuevo = contenedorNombre.value;
  let emailNuevo = contenedorEmail.value;
  let telefonoNuevo = contenedorTelefono.value;
  let documentoNuevo = contenedorDocumento.value;

  const updateUser = {};

  if (nombreNuevo !== nombreOriginal) {
    updateUser.nombre = nombreNuevo;
  }
  if (emailNuevo !== emailOriginal) {
    updateUser.email = emailNuevo;
  }
  if (telefonoNuevo !== telefonoOriginal) {
    updateUser.telefono = telefonoNuevo;
  }
  if (documentoNuevo !== documentoOriginal) {
    updateUser.documento = documentoNuevo;
  }

  // Si no hay cambios, no hacer nada
  if (Object.keys(updateUser).length === 0) {
    cancelarEdicion();
    return;
  }

  Swal.fire({
    title: "¿Esta seguro de guardar los cambios?",
    showDenyButton: true,
    confirmButtonText: "Guardar",
    denyButtonText: `Cancelar`,
    customClass: {
      confirmButton: "btn btn-primary text-white",
      denyButton: "btn btn-secondary text-white",
    },
  }).then(async (result) => {
    if (result.isConfirmed) {
      try {
        await userService.updateUser(idUser, updateUser);
        Swal.fire("cambios guardados!", "", "success");

        // Actualizar objeto usuario local
        for (let key in updateUser) {
          usuario[key] = updateUser[key];
        }

        // Actualizar localStorage
        localStorage.setItem("user", JSON.stringify(usuario));

        // Actualizar valores originales
        nombreOriginal = usuario.nombre;
        emailOriginal = usuario.email;
        telefonoOriginal = usuario.telefono;
        documentoOriginal = usuario.documento;

        // Actualizar campos y estado
        actualizarValoresCampos();

        botonEditarPerfil.classList.remove("d-none");
        botonAceptar.classList.add("d-none");
        botonCancelar.classList.add("d-none");
      } catch (error) {
        Swal.fire("Error", "No se pudieron guardar los cambios", "error");
        cancelarEdicion();
      }
    } else if (result.isDenied) {
      cancelarEdicion();
    }
  });
}

export { init };
