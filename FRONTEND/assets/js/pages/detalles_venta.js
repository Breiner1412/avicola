// import { loadContent } from "../main.js";
import { detalleVentaService } from '../api/detalle_venta.service.js';
import { ventaService } from "../api/venta.service.js";
import { stockService } from "../api/stock.service.js";
import {rescueService} from "../api/salvamento.service.js";

// =========================
// VARIABLES GLOBALES
// =========================
let modalInstance = null; // Guardará la instancia del modal de Bootstrap
let createModalInstance = null;
let originalMail = null;

let detallesVenta = [];
let idVentaReciente = null; 
let ventaDataGlobal = null;

const tableBody = document.getElementById('detalles-table-body');
const botonAgregar = document.getElementById('createDetalle');

// =========================
// UTILIDADES / HELPERS
// =========================
function getSelectMetodoPago() {
    return document.getElementById('metodo_pago');
}

const swalWithBootstrapButtons = Swal.mixin({
    customClass: {
        confirmButton: 'btn btn-success ms-2',
        cancelButton: 'btn btn-secondary'
    },
    buttonsStyling: false
});

function obtenerDatosVenta() {
    try {
        const ventaData = localStorage.getItem('data_venta');
        if (ventaData) {
            const data = JSON.parse(ventaData);
            console.log("Datos de venta recuperados:", data);
            idVentaReciente = data.id_venta;
            ventaDataGlobal = data;
            return data;
        }
        return null;
    } catch (error) {
        console.error("Error al obtener datos de venta:", error);
        return null;
    }
}

function limpiarVentaActiva() {
    localStorage.removeItem('data_venta');
    detallesVenta = [];
    ventaDataGlobal = null;
    idVentaReciente = null;
}

// =========================
// MOSTRAR / CARGAR DATOS DE VENTA
// =========================
function mostrarInformacionVenta(ventaData) {
    const container = document.getElementById('venta-info-container');
    const infoPrincipalVenta = document.getElementById('info-venta');

    if (!ventaData) {
        infoPrincipalVenta.classList.add('d-none');
        container.innerHTML = `
            <div class="col-12 text-center">
                <p class="text-danger">No se encontró información de la venta</p>
            </div>
        `;
        return;
    }

    const inputVendedor = document.getElementById('nombre_vendedor');
    const inputFecha = document.getElementById('fecha_venta');
    const inputIdVenta = document.getElementById('id_venta');

    inputVendedor.value = ventaData.nombre_usuario;
    inputIdVenta.value = `#${ventaData.id_venta}`;

    if (ventaData.fecha_hora) {
        const fecha = new Date(ventaData.fecha_hora).toISOString().split('T')[0];
        inputFecha.value = fecha;
    }
    
    // Formatear la fecha (si viene en formato ISO)
    // const fecha = ventaData.fecha_hora ? 
    //     new Date(ventaData.fecha_hora).toLocaleDateString('es-ES') : 
    //     'Fecha no disponible';
    cargarMetodosPago(ventaData.tipo_pago);
}

async function cargarMetodosPago(idMetodoSeleccionado = null) {
    const selectMetodoPago = getSelectMetodoPago();
    selectMetodoPago.innerHTML = '';
    console.log('hoda'); 

    if (idMetodoSeleccionado === null) {
        const optionPlaceholder = document.createElement('option');
        optionPlaceholder.textContent = 'Seleccione un método';
        optionPlaceholder.selected = true;
        selectMetodoPago.appendChild(optionPlaceholder);
    }

    try {
        const metodos = await ventaService.getMetodosPago();
        console.log(metodos);
        metodos.forEach(metodo => {
            if(metodo.estado === true){
                const option = document.createElement('option');
                option.value = metodo.id_tipo;
                option.textContent = metodo.nombre;

                if (metodo.id_tipo == idMetodoSeleccionado) {
                    option.selected = true;
                }

                selectMetodoPago.appendChild(option);
            }
        });

    } catch (error) {
        console.error("Error cargando métodos de pago:", error);
    }
}

async function handleMetodoPagoChange(event) {
    const cambioMetodoPago = event.target.value;
    if (!cambioMetodoPago || !idVentaReciente) return;

    try {
        await ventaService.updateVenta(idVentaReciente, {
            tipo_pago: cambioMetodoPago
        });
        ventaDataGlobal.tipo_pago = cambioMetodoPago;
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'No se pudo actualizar el método de pago'
        });
    }
}

// =========================
// CREAR DETALLE
// =========================
async function handleCreateDetalle(event) {
    event.preventDefault();
    console.log('Si, soy el botón AJAJAJAJ'); 

    const idProducto = document.getElementById('productos_select');
    const cantidad = document.getElementById('cantidad').value;
    const valorDescuento = document.getElementById('descuento').value || 0;
    const precioVenta = document.getElementById('precio_unitario').value;
    const selectDetalle = document.getElementById('tipo_producto').value;

    //capturo valores especifocs del select de productos: 
    let nombre_producto_seleccionado = idProducto.options[idProducto.selectedIndex].dataset.nombre;
    
    if (!idProducto || !cantidad || !precioVenta) {
        Swal.fire({
            icon: 'warning',
            title: 'Campos incompletos',
            text: 'Debes completar todos los campos obligatorios'
        });
        return;
    }

    if (cantidad <= 0 || precioVenta <= 0 || valorDescuento < 0) {
        Swal.fire({
            icon: 'warning',
            title: 'Valores inválidos',
            text: 'Cantidad, precio o descuento no son válidos'
        });
        return;
    }

    const productoExistente = detallesVenta.find(
        detalle => detalle.id_producto === idProducto.value && 
        detalle.tipo_detalle === (selectDetalle === '1' ? 'Huevos' : 'Salvamento')
    );

    if (productoExistente) {
        Swal.fire({
            icon: 'info',
            title: 'Producto ya agregado',
            text: 'Este producto ya se encuentra en los detalles de la venta. Puedes editar la información desde la tabla si es necesario.',
            confirmButtonText: 'Entendido',
            customClass: {
                confirmButton: 'btn btn-success'
            }
        });
        return;
    }

    let descuentoPesos = (precioVenta * valorDescuento)/100; 
    
    const detallesData = { 
        id_producto: idProducto.value,
        cantidad: cantidad,
        id_venta: idVentaReciente, 
        valor_descuento: descuentoPesos,
        precio_venta: precioVenta
    };

    const swalWithBootstrapButtonsCreateDetalle = Swal.mixin({
        customClass: {
            confirmButton: "btn btn-success ms-2",
            cancelButton: "btn btn-danger"
        },
        buttonsStyling: false
    });

    try {
        botonAgregar.disabled = true;
        botonAgregar.textContent = 'Agregando...';
        
        let respuesta_crear_detalle;
        let id_creado; 
        if(selectDetalle === '1'){
            respuesta_crear_detalle = await detalleVentaService.createDetalleHuevos(detallesData); 
            id_creado = respuesta_crear_detalle.id_detalle_huevo;
            // console.log('Detalle Huevo creado exitosamente', respuesta_crear_detalle);
            console.log('si soy ', id_creado); 
        }else if (selectDetalle === '2'){ 
            respuesta_crear_detalle =  await detalleVentaService.createDetalleSalvamento(detallesData); 
            id_creado = respuesta_crear_detalle.id_detalle_salvamento;
            console.log('q pasouuu id', id_creado); 
            console.log('Detalle Salvamento creado exitosamente', respuesta_crear_detalle);
        }
        
        let data = {
            id_producto: idProducto.value,
            id_detalle : id_creado, 
            tipo_detalle: selectDetalle === '1' ? 'Huevos' : 'Salvamento', 
            nombre_producto: nombre_producto_seleccionado,
            cantidad: cantidad,
            id_venta: idVentaReciente, 
            valor_descuento: descuentoPesos,
            descuento_porcentaje: valorDescuento,
            precio_venta: precioVenta
        };

        detallesVenta.push(data); 
        console.log(detallesVenta);
        imprimirDetalles();

        document.getElementById('productos_select').value = "";
        document.getElementById('cantidad').value = "";
        document.getElementById('descuento').value = "";
        document.getElementById('precio_unitario').value = "";

    } catch (error) {
        console.error("Error:", error);
        await swalWithBootstrapButtonsCreateDetalle.fire({
            title: ('Error al agregar el producto'),
            text:  error.message,
            icon: "error"
        });
    } finally {
        botonAgregar.disabled = false;
        botonAgregar.textContent = 'Agregar Producto';
    }
}

// =========================
// LISTAR / CALCULAR TOTALES
// =========================
async function imprimirDetalles(){
    const tableBody = document.getElementById('detalles-table-body');
    tableBody.innerHTML = '';

    // let detalles = await detalleVentaService.getDettallesVenta(idVentaReciente);
    detallesVenta.forEach(element => {
        const fila = document.createElement('tr');

        const colTipo = document.createElement('td');
        colTipo.textContent = element.tipo_detalle;

        const colProducto = document.createElement('td');
        colProducto.textContent = element.nombre_producto;

        const colCantidad = document.createElement('td');
        colCantidad.textContent = element.cantidad;

        const colPrecio = document.createElement('td');
        colPrecio.textContent = `$${parseFloat(element.precio_venta).toFixed(2)}`;

        const colDescuentoPorcentaje = document.createElement('td');
        colDescuentoPorcentaje.textContent = element.descuento_porcentaje;

        const colDescuentoPesos = document.createElement('td');
        let descuentoColPesos = element.valor_descuento * element.cantidad;
        colDescuentoPesos.textContent = `$${descuentoColPesos.toLocaleString('es-CO')}`;

        const colSubTotal = document.createElement('td'); 
        colSubTotal.textContent = `$${calcularSubtotal(element).toLocaleString('es-CO')}`;

        const colAcciones = document.createElement('td');
        
        const botonEdit = document.createElement('button');
        botonEdit.classList.add('btn', 'btn-success', 'btn-sm', 'btn-edit-detalle');
        botonEdit.setAttribute('data-id-producto', element.id_producto);
        botonEdit.setAttribute('data-tipo-producto', element.tipo_detalle);
        botonEdit.setAttribute('data-detalle-id', element.id_detalle);
        botonEdit.innerHTML = '<i class="fa-regular fa-pen-to-square"></i>';

        const botonDelete = document.createElement('button');
        botonDelete.classList.add('btn', 'btn-secondary', 'btn-sm', 'ms-2', 'btn-delete-detalle');
        botonDelete.setAttribute('data-tipo-producto', element.tipo_detalle);
        botonDelete.setAttribute('data-detalle-id', element.id_detalle);
        botonDelete.innerHTML = '<i class="fa-regular fa-trash-can"></i>';

        colAcciones.appendChild(botonEdit);
        colAcciones.appendChild(botonDelete);
        
        fila.appendChild(colTipo);
        fila.appendChild(colProducto);
        fila.appendChild(colCantidad);
        fila.appendChild(colPrecio);
        fila.appendChild(colDescuentoPorcentaje);
        fila.appendChild(colDescuentoPesos);
        fila.appendChild(colSubTotal);
        fila.appendChild(colAcciones);
        
        tableBody.appendChild(fila);
    });

    calcularTotal(detallesVenta);
}

function calcularSubtotal(producto) {
    return (producto.precio_venta - producto.valor_descuento) * producto.cantidad;
}

function calcularTotal(detalles){
    const descuentoElement = document.getElementById('total-descuento');
    const totalElement = document.getElementById('total-venta');

    if(detalles.length === 0){
        descuentoElement.textContent = "$0";
        totalElement.textContent = "$0";
        return; 
    }

    let totalVenta = 0;
    let totalDescuento = 0;
    detalles.forEach(producto => {
        let subtotal = calcularSubtotal(producto); 
        totalVenta += subtotal;
        totalDescuento += producto.valor_descuento * producto.cantidad;
    });
    
    descuentoElement.textContent = `$${totalDescuento.toLocaleString('es-CO')}`;
    totalElement.textContent = `$${totalVenta.toLocaleString('es-CO')}`;
}

// =========================
// EDITAR / ELIMINAR DETALLE
// =========================
//Modales update, función q se activa cuando le den click al icono de editar or eliminar
async function handleTableClick(event) {
    const editButton = event.target.closest('.btn-edit-detalle');
    console.log("aqui toooy")
    if (editButton) {
        // Para debuggear, muestra TODOS los atributos data-*
        console.log("Todos los dataset del botón:", editButton.dataset);

        const id = editButton.dataset.detalleId;          
        let tipo_product_edit = editButton.dataset.tipoProducto;  
        let id_producto = editButton.dataset.idProducto;

        console.log(`¿quien eres? q soy????`); 
        // console.log(id, tipo_product_edit, id_producto)
        //************************************************* */
        console.log(`Edit detalle with id: ${id}`);
        openEditModal(id, tipo_product_edit, id_producto);
        return;
    }

    const deleteButton = event.target.closest('.btn-delete-detalle');
    if(deleteButton){
        let tipo_producto_delete = deleteButton.dataset.tipoProducto;
        let id_detalle_delete = deleteButton.dataset.detalleId;

        const confirmacion = await swalWithBootstrapButtons.fire({
            title: "¿Eliminar este detalle?",
            text: "Esta acción NO se puede deshacer.",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Sí, eliminar",
            cancelButtonText: "No, cancelar",
            reverseButtons: true
        });

        if (confirmacion.isConfirmed) {
            try {
                await detalleVentaService.deleteDetalle(id_detalle_delete, tipo_producto_delete);
                detallesVenta = detallesVenta.filter(detalle => detalle.id_detalle != id_detalle_delete);
                imprimirDetalles(detallesVenta);
            } catch (error) {
                Swal.fire({
                    icon: "error",
                    title: 'Ups...',
                    text: "No se pudo eliminar el detalle.",
                });
            }
        }
    }
}

// función asincronica si se traen los datos desde el back
// async function openEditModal(id, tipo_product, id_producto) {
//     console.log(id, tipo_product, id_producto);  
//     const modalElement = document.getElementById('edit-detalle-modal');

//     if (!modalInstance) {
//         modalInstance = new bootstrap.Modal(modalElement);
//     }
//     try {
//         const select_edit = document.getElementById("select-edit-producto");
//         const detalle = await detalleVentaService.getDetalleVenta(id, tipo_product);
//         console.log(detalle); 

//         let productos_select_edit;

//         if(tipo_product == 'Huevos'){
//             productos_select_edit = await detalleVentaService.getProductosStock()
//         }else if(tipo_product == 'Salvamento'){
//             productos_select_edit = await detalleVentaService.getProductosSalvamento()

//         }
        
//         select_edit.innerHTML = '';
//         productos_select_edit.forEach(element => {
//             const option_edit = document.createElement("option");
//             option_edit.value =  tipo_product == 'Huevos' ? element.id_producto : element.id_salvamento;
//             option_edit.dataset.tipoProducto = tipo_product;
//             option_edit.textContent = tipo_product == 'Huevos' ? `Huevo ${element.color} ${element.tamanio} ${element.unidad_medida}` : element.raza;

//             select_edit.appendChild(option_edit);
//         });

//         select_edit.value = id_producto;


//         const input_edit_cantidad = document.getElementById("edit-cantidad");
//         const input_edit_descuento = document.getElementById("edit-descuento");
//         const input_edit_precio_unitario = document.getElementById("edit-precio_unitario");
//         const input_id_detalle_edit = document.getElementById("edit-detalle-id");

//         console.log("acaaaaaaa", detalle);
//         input_edit_cantidad.value = detalle.cantidad;
//         input_edit_descuento.value = detalle.valor_descuento;
//         input_edit_precio_unitario.value = detalle.precio_venta;
//         input_id_detalle_edit.value = detalle.id_detalle;

//         // console.log("aqui: ", detalle)
//         modalInstance.show();

//     } catch (error) {
//         console.error(`Error al obtener datos del detalle ${detalle.id_detalle}`, error);
//         Swal.fire({
//             icon: "error",
//             title: 'Ups...',
//             text: "Error al obtener datos del detalle",
//         });
//     }
// }

//función asincronica si se traen los datos desde el array
async function openEditModal(id, tipo_product, id_producto) {
    const modalElement = document.getElementById('edit-detalle-modal');

    if (!modalInstance) {
        modalInstance = new bootstrap.Modal(modalElement);
    }

    // Buscar el detalle dentro del array detallesVenta
    const detalleEncontrado = detallesVenta.find(det => det.id_detalle == id);

    if (!detalleEncontrado) {
        Swal.fire({
            icon: "error",
            title: 'Ups...',
            text: "No pude encontrar el detalle seleccionado",
        });
        return;
    }

    const select_edit = document.getElementById("select-edit-producto");
    const input_edit_cantidad = document.getElementById("edit-cantidad");
    const input_edit_descuento = document.getElementById("edit-descuento");
    const input_edit_precio_unitario = document.getElementById("edit-precio_unitario");
    const input_id_detalle_edit = document.getElementById("edit-detalle-id");

    let productosDisponibles = [];

    if (tipo_product === "Huevos") {
        productosDisponibles = await detalleVentaService.getProductosStock();
    } else {
        productosDisponibles = await detalleVentaService.getProductosSalvamento();
    }

    select_edit.innerHTML = '';

    productosDisponibles.forEach(producto => {
        const option = document.createElement("option");
        option.value = tipo_product == "Huevos" ? producto.id_producto : producto.id_salvamento;
        option.dataset.tipoProducto = tipo_product;
        option.textContent = tipo_product == "Huevos"
            ? `Huevo ${producto.color} ${producto.tamanio} ${producto.unidad_medida}`
            : producto.raza;
        select_edit.appendChild(option);
    });

    select_edit.value = id_producto;

    input_edit_cantidad.value = detalleEncontrado.cantidad;
    input_edit_descuento.value = detalleEncontrado.descuento_porcentaje;
    input_edit_precio_unitario.value = detalleEncontrado.precio_venta;
    input_id_detalle_edit.value = detalleEncontrado.id_detalle;

    modalInstance.show();
}

async function handleUpdateSubmit(event) {
    event.preventDefault();
    // captutamos lo indispensable
    const detalleId = document.getElementById('edit-detalle-id').value;
    const selectProductoEdit = document.getElementById('select-edit-producto');
    const selectedOption = selectProductoEdit.options[selectProductoEdit.selectedIndex];
    const tipoProducto = selectedOption.dataset.tipoProducto;

    //capturamos los posibles inputs q puede manipular
    const id_producto_cambio = parseInt(selectProductoEdit.value);
    const cantidad_cambio = parseInt(document.getElementById('edit-cantidad').value);
    const descuento_cambio = parseFloat(document.getElementById('edit-descuento').value);
    const precio_cambio = parseFloat(document.getElementById('edit-precio_unitario').value); 

    const posibles_errores = []; 
    if (cantidad_cambio <= 0) posibles_errores.push('Cantidad debe ser mayor a 0');
    if (precio_cambio <= 0) posibles_errores.push('Precio debe ser mayor a 0');
    if (descuento_cambio < 0) posibles_errores.push('Descuento debe ser mayor o igual a 0');

    if(posibles_errores.length > 0){
        Swal.fire({
            icon: "warning",
            title: "Datos incorrectos",
            text: posibles_errores.join('\n'), 
        });
        return;
    }

    let descuento_cambio_en_pesos = (precio_cambio * descuento_cambio)/100; 

    const updatedData = {
        id_producto: id_producto_cambio,
        cantidad: cantidad_cambio,
        valor_descuento: descuento_cambio_en_pesos,
        precio_venta: precio_cambio
    };

    const swalInstance = Swal.fire({
        title: 'Actualizando...',
        html: '<div class="spinner-border text-primary" role="status"></div>',
        showConfirmButton: false,
        allowOutsideClick: false,
        backdrop: 'rgba(0,0,0,0.4)'
    });

    try {
        await detalleVentaService.updateDetalle(detalleId, updatedData, tipoProducto);

        // const nombre_producto_nuevo = selectProductoEdit.options[selectProductoEdit.selectedIndex].dataset.nombre;
        const nombre_producto_nuevo = selectedOption.textContent.trim();

        detallesVenta = detallesVenta.map(detalle => {
            if(detalle.id_detalle == detalleId){
                return {
                    ...detalle,
                    id_producto: id_producto_cambio,
                    cantidad: cantidad_cambio,
                    valor_descuento: descuento_cambio_en_pesos,
                    descuento_porcentaje: descuento_cambio,
                    precio_venta: precio_cambio,
                    nombre_producto: nombre_producto_nuevo
                };
            }
            return detalle;
        });

        swalInstance.close();
        modalInstance.hide();
        await imprimirDetalles(); // Recargamos la tabla para ver los cambios

        Swal.fire({
            icon: 'success',
            title: "Exito",
            text: "¡Detalle venta actualizado exitosamente!",
            confirmButtonColor: '#28a745'
        });
        
    } catch (error) {
        console.error(`Error al actualizar detalle ${detalleId}:`, error);
        console.error(error);
        Swal.fire({
            icon: "error",
            title: ('Error al actualizar detalle'),
            text:  error.message,
            customClass: {
                confirmButton: 'btn btn-success ms-2'
            }
        });
    }
}

// =========================
// INIT
// =========================
export const init = () => {
    console.log('****************');
    console.log("Módulo de detalles inicializado");

    const ventaData = obtenerDatosVenta();

    if (!ventaData || !idVentaReciente) {
        console.log("No hay venta activa, esperando nueva venta");
    }

    console.log(`Trabajando con venta ID: ${idVentaReciente}`);
    console.log("Datos de la venta:", ventaData);

    mostrarInformacionVenta(ventaData);

    const tableBody = document.getElementById('detalles-table-body');
    const botonAgregar = document.getElementById('createDetalle');
    const editForm = document.getElementById('edit-detalle-form');
    const selectMetodoPago = document.getElementById('metodo_pago');
    const selectDetalle = document.getElementById('tipo_producto');
    const productos_select = document.getElementById('productos_select');
    const button_guardar_venta = document.getElementById("guardar_venta");
    const button_cancelar_venta = document.getElementById("cancelar_venta");

    if (!tableBody || !botonAgregar || !editForm) {
        console.warn("Elementos del DOM no encontrados");
        return;
    }

    if (selectMetodoPago) {
        selectMetodoPago.removeEventListener('change', handleMetodoPagoChange);
        selectMetodoPago.addEventListener('change', handleMetodoPagoChange);
    }

    const cargarProductos = async (typeDetalle) => {
        productos_select.innerHTML = '<option value="">Selecciona producto</option>';
        let placeholderCantidad = document.getElementById("cantidad");
        
        // Reset inicial
        placeholderCantidad.placeholder = "Ingrese cantidad";

        // Eliminar listeners previos (opcional pero recomendado)
        productos_select.onchange = async () => {
            if (productos_select.value === "") {
                placeholderCantidad.placeholder = "Ingrese cantidad";
                return;
            }

            let cantidadDisponibleStock = typeDetalle == "1" ? await stockService.GetStockById(productos_select.value) : await rescueService.getRescueById(productos_select.value);
            placeholderCantidad.placeholder = `cantidad disponible: ${ typeDetalle == "1" ? cantidadDisponibleStock.cantidad_disponible : cantidadDisponibleStock.cantidad_gallinas}`;
        };
        try {
            if (typeDetalle === "1") {
                const productos = await detalleVentaService.getProductosStock();
                productos.forEach(producto => {
                    const option = document.createElement('option');
                    option.value = producto.id_producto;
                    option.textContent = `Huevo ${producto.color}-${producto.tamanio}-${producto.unidad_medida}`;
                    option.dataset.nombre = option.textContent;
                    productos_select.appendChild(option);
                });
            } else if (typeDetalle === "2") {
                const productos = await detalleVentaService.getProductosSalvamento();
                productos.forEach(producto => {
                    const option = document.createElement('option');
                    option.value = producto.id_salvamento;
                    option.textContent = producto.raza;
                    option.dataset.nombre = producto.raza;
                    productos_select.appendChild(option);
                });
            }
        } catch (error) {
            console.error("Error cargando productos:", error);
        }
    };

    selectDetalle.removeEventListener('change', handleTipoProductoChange);
    selectDetalle.addEventListener('change', handleTipoProductoChange);

    function handleTipoProductoChange(event) {
        cargarProductos(event.target.value);
    }
    cargarProductos("1");

    tableBody.removeEventListener('click', handleTableClick);
    tableBody.addEventListener('click', handleTableClick);

    botonAgregar.removeEventListener('click', handleCreateDetalle);
    botonAgregar.addEventListener('click', handleCreateDetalle);

    editForm.removeEventListener('submit', handleUpdateSubmit);
    editForm.addEventListener('submit', handleUpdateSubmit);

    if (button_guardar_venta) {
        button_guardar_venta.onclick = (event) => {
            event.preventDefault();

            if (detallesVenta.length === 0) {
                Swal.fire({
                    icon: "error",
                    title: 'No se puede registrar la venta',
                    text: "No se puede registrar venta sin detalles creados.",
                    confirmButtonColor: '#28a745'
                });
                return;
            }

            Swal.fire({
                icon: 'success',
                title: 'Venta guardada con éxito',
                text: 'Detalles añadidos exitosamente',
                confirmButtonColor: '#28a745'
            });

            limpiarVentaActiva();
            loadContent(button_guardar_venta.dataset.page);
        };
    }

    if (button_cancelar_venta) {
        button_cancelar_venta.onclick = async () => {
            const confirmacion = await swalWithBootstrapButtons.fire({
                title: "¿Está seguro de cancelar la venta?",
                text: "Esta acción NO se puede deshacer.",
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: "Sí, cancelar venta",
                cancelButtonText: "No, seguir modificando",
                reverseButtons: true
            });

            if (!confirmacion.isConfirmed) return;

            try {
                await ventaService.cambiarEstado(idVentaReciente, 0);

                Swal.fire({
                    icon: 'warning',
                    title: 'Venta cancelada',
                    text: 'La venta fue cancelada correctamente',
                    confirmButtonColor: '#28a745'
                });

                limpiarVentaActiva();
                loadContent(button_cancelar_venta.dataset.page);

            } catch (error) {
                console.error("Error al cancelar venta:", error);
                Swal.fire({
                    icon: "error",
                    title: 'Error al cancelar venta',
                    text: error.message
                });
            }
        };
    }
};

//funcion para inicializar
// export const init = () => {
//     console.log('****************');
//     console.log("Módulo de detalles inicializado");
//     const ventaData = obtenerDatosVenta(); 

//     if (idVentaReciente) {
//         console.log(`Trabajando con venta ID: ${idVentaReciente}`);
//         console.log("Estos son sus datos:", ventaData); 

//         mostrarInformacionVenta(ventaData);

//         // configurarBotonEditar(); 

//     } else {
//         console.log("No se encontró data de venta");
//         Swal.fire({
//             icon: "error",
//             title: 'Ups...',
//             text: "No se encontró data de venta",
//         });
//     }

//     const selectMetodoPago = document.getElementById('metodo_pago');

//     if (selectMetodoPago) {
//         selectMetodoPago.addEventListener('change', async (event) => {
//             const cambioMetodoPago = event.target.value;
//             if (!cambioMetodoPago) return;

//             try {
//                 await ventaService.updateVenta(idVentaReciente, {
//                     tipo_pago: cambioMetodoPago
//                 });

//                 ventaDataGlobal.tipo_pago = cambioMetodoPago;

//             } catch (error) {
//                 console.error(error);
//                 Swal.fire({
//                     icon: 'error',
//                     title: 'Error',
//                     text: 'No se pudo actualizar el método de pago'
//                 });
//             }
//         });
//     }

//     const selectDetalle = document.getElementById('tipo_producto');
//     const productos_select = document.getElementById('productos_select');

//     // Función para cargar productos basado en el tipo
//     async function cargarProductos(typeDetalle) {
//         productos_select.innerHTML = '<option value="">Selecciona producto</option>';
        
//         if (typeDetalle === "1"){
//             try {
//                 const productos = await detalleVentaService.getProductosStock();
//                 console.log("Productos:", productos);

//                 productos.forEach(producto => {
//                     const opcion = document.createElement('option');
//                     opcion.value = producto.id_producto;
//                     opcion.textContent = `Huevo ${producto.color}-${producto.tamanio}-${producto.unidad_medida}`;
//                     opcion.dataset.nombre = `Huevo ${producto.color}-${producto.tamanio}-${producto.unidad_medida}`;
//                     productos_select.appendChild(opcion); 
//                 });
//             } catch (error) {
//                 console.error("Error:", error);
//             }  
//         } else if (typeDetalle === "2") {
//             try {
//                 const productos = await detalleVentaService.getProductosSalvamento();
//                 console.log("Productos", productos);
                
//                 productos.forEach(producto => {
//                     const opcion = document.createElement('option');
//                     opcion.value = producto.id_salvamento;
//                     opcion.textContent = producto.raza;
//                     opcion.dataset.nombre = producto.raza;
//                     productos_select.appendChild(opcion); 
//                 });
//             } catch (error) {
//                 console.error("Error:", error);
//             }  
//         }
//     }

//     // Event listener para cuando cambie el tipo
//     selectDetalle.addEventListener('change', async function(event){
//         let typeDetalle = event.target.value; 
//         console.log(typeDetalle); 
//         await cargarProductos(typeDetalle);
//     });

//     // Cargar productos de huevos automáticamente al iniciar
//     cargarProductos('1'); // '1' es el valor para Huevos
//     const editForm = document.getElementById('edit-detalle-form');

//     tableBody.removeEventListener('click', handleTableClick);
//     tableBody.addEventListener('click', handleTableClick);
//     editForm.removeEventListener('submit', handleUpdateSubmit);
//     editForm.addEventListener('submit', handleUpdateSubmit);

//     botonAgregar.removeEventListener('click', handleCreateDetalle);
//     botonAgregar.addEventListener('click', handleCreateDetalle);
//     const button_guardar_venta = document.getElementById("guardar_venta");

    

//     if (button_guardar_venta) {
//         button_guardar_venta.addEventListener("click", (event) => {
//             event.preventDefault();
//             console.log("¡Botón de venta clickeado!");

//             if(detallesVenta.length == 0){
//                 Swal.fire({
//                     icon: "error",
//                     title: 'No se puede registrar la venta',
//                     text: "No se puede registrar venta sin detalles creados.",
//                     confirmButtonColor: '#28a745'
//                 });
//                 return; 
//             }   
//             // limpiar el localStorage
//             // localStorage.clear(); 
            
//             // console.log("LocalStorage limpiado");
//             Swal.fire({
//                 icon: 'success',
//                 title: 'Venta guardada con exito',
//                 text: 'Detalles añadidos exitosamente',
//                 confirmButtonColor: '#28a745'
//             });
//             const pageToLoad = button_guardar_venta.dataset.page;
//             console.log(`Navegando a: ${pageToLoad}`);
            
//             // Usar la función de navegación
//             loadContent(pageToLoad);
//         });
//     }

//     const button_cancelar_venta = document.getElementById("cancelar_venta"); 

//     if(button_cancelar_venta){
//         button_cancelar_venta.addEventListener("click", async (event) => {
//             console.log("¿Por que me quieres cancelar :( ?"); 

//             const confirmar_cancelacion = await swalWithBootstrapButtons.fire({
//                 title: "¿Está seguro de cancelar la venta?",
//                 text: "Esta acción NO se puede deshacer.",
//                 icon: "warning",
//                 showCancelButton: true,
//                 confirmButtonText: "Sí, cancelar venta", 
//                 cancelButtonText: "No, seguir modificando",
//                 reverseButtons: true
//             });


//             if(confirmar_cancelacion.isConfirmed){
//                 const swalInstance = Swal.fire({
//                     title: 'Cancelando venta...',
//                     html: '<div class="spinner-border text-primary" role="status"></div>',
//                     showConfirmButton: false,
//                     allowOutsideClick: false,
//                     backdrop: 'rgba(0,0,0,0.4)'
//                 });

//                 try{
//                     console.log("heeeey");

//                     const respuestaServicioCancelar = await ventaService.cambiarEstado(idVentaReciente, 0);
//                     console.log(respuestaServicioCancelar); 

//                     const pageToLoad = button_cancelar_venta.dataset.page;
//                     console.log(`Navegando a: ${pageToLoad}`);

//                     swalInstance.close; 
//                     Swal.fire({
//                         icon: 'warning',
//                         title: 'Venta cancelada',
//                         text: 'La venta fue cancelada correctamente'
//                     });

//                     localStorage.removeItem('data_venta');
//                     detallesVenta = [];
//                     ventaDataGlobal = null;
//                     idVentaReciente = null;


//                     loadContent(pageToLoad); 
//                 }catch(error){
//                     console.error(`Error al cancelar venta${idVentaReciente}:`, error);
//                     Swal.fire({
//                         icon: "error",
//                         title: ('Error al cancelar venta'),
//                         text:  error.message,
//                     });
//                 }
//             }

//         })
//     }
// };
