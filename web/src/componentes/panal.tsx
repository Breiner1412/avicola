/** Huevos por panal: el empaque de venta de la granja. */
export const HUEVOS_POR_PANAL = 30;

/** Cuenta los huevos en panales completos y los que quedan sueltos. */
export function enPanales(huevos: number) {
  const total = Math.max(0, Math.floor(huevos));
  return { panales: Math.floor(total / HUEVOS_POR_PANAL), sueltos: total % HUEVOS_POR_PANAL };
}

/** Un panal de 5 x 6 con los huevos sueltos en amarillo. Solo decora: el texto dice la cifra. */
export function Panal({ llenos, className = "" }: { llenos: number; className?: string }) {
  return (
    <span aria-hidden="true" className={`grid grid-cols-6 gap-1 rounded-md bg-white/10 p-2 ${className}`}>
      {Array.from({ length: HUEVOS_POR_PANAL }, (_, i) => (
        <span
          key={i}
          className={`block h-[13px] w-[11px] rounded-[50%_50%_46%_46%/58%_58%_42%_42%] ${
            i < llenos ? "bg-yema" : "bg-white/15"
          }`}
        />
      ))}
    </span>
  );
}
