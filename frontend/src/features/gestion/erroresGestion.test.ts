import { ErrorApi } from "../../shared/api/errorApi";
import { interpretarErrorGestion } from "./erroresGestion";

const CONFIG = {
  campos: { email: "email", nombre: "nombre" },
  duplicado: {
    nombre: "Ya existe un sillón con ese nombre.",
  },
  codigos: {
    duracion_invalida: {
      campo: "duracion",
      texto: "La duración debe ser múltiplo de 5, de 5 a 480 minutos.",
    },
    franja_superpuesta: { texto: "Se superpone con otra franja de ese día." },
  },
} as const;

function validacion(campos: Array<string | null>) {
  return new ErrorApi({
    status: 422,
    codigo: "validacion",
    mensaje: "Revisá los datos ingresados.",
    errores: campos.map((campo) => ({
      campo,
      mensaje: "el email debe tener la forma algo@algo",
    })),
  });
}

describe("interpretarErrorGestion", () => {
  it("validación con un campo conocido lo marca, sin mostrar el msg", () => {
    const r = interpretarErrorGestion(validacion(["email"]), CONFIG);

    expect(r.porCampo).toEqual({ email: "Revisá este campo." });
    expect(r.general).toBeNull();
    expect(JSON.stringify(r)).not.toContain("algo@algo");
  });

  it("validación con un campo que el formulario no tiene es un error general", () => {
    const r = interpretarErrorGestion(validacion(["telefono_raro"]), CONFIG);

    expect(r.porCampo).toEqual({});
    expect(r.general).toBe("Revisá los datos ingresados.");
  });

  it("validación sin campo es un error general", () => {
    const r = interpretarErrorGestion(validacion([null]), CONFIG);

    expect(r.general).toBe("Revisá los datos ingresados.");
  });

  it("validación con un campo conocido y otro desconocido muestra ambos", () => {
    const r = interpretarErrorGestion(validacion(["email", null]), CONFIG);

    expect(r.porCampo).toEqual({ email: "Revisá este campo." });
    expect(r.general).toBe("Revisá los datos ingresados.");
  });

  it("recurso_duplicado se marca en el campo indicado por la API", () => {
    const error = new ErrorApi({
      status: 409,
      codigo: "recurso_duplicado",
      mensaje: "x",
      datos: { campo: "nombre" },
    });

    expect(interpretarErrorGestion(error, CONFIG).porCampo).toEqual({
      nombre: "Ya existe un sillón con ese nombre.",
    });
  });

  it("recurso_duplicado de un campo sin texto propio cae al error general del cliente", () => {
    const error = new ErrorApi({
      status: 409,
      codigo: "recurso_duplicado",
      mensaje: "Ocurrió un error. Intentá de nuevo.",
      datos: { campo: "otro" },
    });

    const r = interpretarErrorGestion(error, CONFIG);

    expect(r.porCampo).toEqual({});
    expect(r.general).toBe("Ocurrió un error. Intentá de nuevo.");
  });

  it("404 recurso_inexistente deja el registro como obsoleto", () => {
    const error = new ErrorApi({
      status: 404,
      codigo: "recurso_inexistente",
      mensaje: "x",
      datos: { recurso: "sillon" },
    });

    const r = interpretarErrorGestion(error, CONFIG);

    expect(r.general).toBe("Este registro ya no existe.");
    expect(r.registroInexistente).toBe(true);
  });

  it("403 se traduce como falta de permiso", () => {
    const error = new ErrorApi({
      status: 403,
      codigo: "rol_insuficiente",
      mensaje: "Solo la recepcionista",
    });

    const r = interpretarErrorGestion(error, CONFIG);

    expect(r.general).toBe("No tenés permiso para esta operación.");
    expect(r.registroInexistente).toBe(false);
  });

  it("una falla de red muestra el mensaje del error", () => {
    const error = new ErrorApi({
      status: 0,
      codigo: null,
      mensaje: "No se pudo conectar con el servidor.",
    });

    expect(interpretarErrorGestion(error, CONFIG).general).toBe(
      "No se pudo conectar con el servidor.",
    );
  });

  it("un código de la pantalla con campo va a ese campo", () => {
    const error = new ErrorApi({
      status: 422,
      codigo: "duracion_invalida",
      mensaje: "texto para desarrolladores",
    });

    const r = interpretarErrorGestion(error, CONFIG);

    expect(r.porCampo).toEqual({
      duracion: "La duración debe ser múltiplo de 5, de 5 a 480 minutos.",
    });
    expect(r.general).toBeNull();
  });

  it("un código de la pantalla sin campo es un error general", () => {
    const error = new ErrorApi({
      status: 409,
      codigo: "franja_superpuesta",
      mensaje: "texto para desarrolladores",
    });

    const r = interpretarErrorGestion(error, CONFIG);

    expect(r.general).toBe("Se superpone con otra franja de ese día.");
    expect(r.porCampo).toEqual({});
  });

  it("un 403 con un código propio de la pantalla usa el texto de la pantalla", () => {
    const error = new ErrorApi({
      status: 403,
      codigo: "profesional_ajeno",
      mensaje: "Solo podés operar sobre tus propios bloqueos",
    });

    const r = interpretarErrorGestion(error, {
      ...CONFIG,
      codigos: {},
    });

    expect(r.general).toBe("No tenés permiso para esta operación.");
  });
});
