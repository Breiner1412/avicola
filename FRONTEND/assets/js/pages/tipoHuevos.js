import { TipoHuevosService } from "../api/tipoHuevo.service.js";
import { shedService } from "../api/shed.service.js";

const tipoHuevos = TipoHuevosService.GetTipoHuevosAll();

async function init(page = 1) {}
export async function cargarTipoHuevos() {
  try {
    const tiposHuevos = await TipoHuevosService.GetTipoHuevosAll();
    const sheds = await shedService.getSheds();

    const select = document.getElementById("create-id-tipo-huevo");
    const selectGalpon = document.getElementById("create-id-galpon");

    const selectTipo = document.getElementById("edit-tamaño");
    const selectEditGalpon = document.querySelector(
      "select#edit-produccion-nombre"
    );

    tiposHuevos.forEach((huevo) => {
      const option = document.createElement("option");
      const optionEdit = document.createElement("option");

      option.value = huevo.id_tipo_huevo;
      option.textContent = `${huevo.Tamaño}`;

      optionEdit.value = huevo.id_tipo_huevo;
      optionEdit.textContent = `${huevo.Tamaño}`;

      select.appendChild(option);
      selectTipo.appendChild(optionEdit);
    });
    select.selectedIndex = 0;
    selectTipo.selectedIndex = 0;

    sheds.forEach((item) => {
      const option = document.createElement("option");
      const optionEditG = document.createElement("option");

      option.value = item.id_galpon;
      option.textContent = `${item.nombre}`;

      optionEditG.value = item.id_galpon;
      optionEditG.textContent = `${item.nombre}`;

      selectGalpon.appendChild(option);
      selectEditGalpon.appendChild(optionEditG);
    });
  } catch {}
}

// Llamar la función
cargarTipoHuevos();
export { init };
