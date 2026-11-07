> Detalla en esta sección los prompts principales utilizados durante la creación del proyecto, que justifiquen el uso de asistentes de código en todas las fases del ciclo de vida del desarrollo. Esperamos un máximo de 3 por sección, principalmente los de creación inicial o los de corrección o adición de funcionalidades que consideres más relevantes.

**Herramienta:** Claude Code (Claude). Los prompts se transcriben como se escribieron; los textos largos pegados se resumen como *(extracto)*. En las secciones 4, 5 y 6 se incluyen además los prompts con los que el asistente delegó el trabajo en subagentes paralelos.

## Índice

1. [Descripción general del producto](#1-descripción-general-del-producto)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Modelo de datos](#3-modelo-de-datos)
4. [Especificación de la API](#4-especificación-de-la-api)
5. [Historias de usuario](#5-historias-de-usuario)
6. [Tickets de trabajo](#6-tickets-de-trabajo)
7. [Pull requests](#7-pull-requests)

---

## 1. Descripción general del producto

**Prompt 1:**

> Crea nuevo repositorio en la carpeta repositories que esté destinado a un proyecto de una app multidispositivo y multinenant para el registro de ventas, dirigida a micronegocios. Debe tener rama master y develop. No crear ninguna carpeta de codigo, pero si el folder docs/ donde se escribirá la documentación técnica que a continuación te compartiré para construirla.

**Prompt 2:**

> *(extracto)* Aquí tienes la plantilla técnica adaptada específicamente a una app multidispositivo y multitenant de registro de ventas para micronegocios, se debe cumplimentar: Contexto del Problema: ¿Cuál es el problema concreto y qué ineficiencia resuelve? Pauta: explica la brecha de digitalización en micronegocios (kioscos, ferreterías, tiendas de barrio), registro rápido de tickets/ventas, gestión de catálogo básico, control de existencias, cierre diario de caja, multi-inquilino y acceso multidispositivo. Out of Scope: facturación electrónica fiscal. Además, quiero agregar la visión de querer incorporar componentes de IA: chat, OCR y la incorporación de almacenamiento de imágenes de productos y corporativa, destacaando que no va a entrar en el MVP, que quedará para desarrollarlo post-MVP.

---

## 2. Arquitectura del Sistema

### **2.1. Diagrama de arquitectura:**

**Prompt 1:**

> *(extracto de la plantilla compartida)* ¿Cuál es el estilo arquitectónico del sistema? Define la arquitectura cliente-servidor API-First (SPA/PWA interactuando vía REST con un backend modular). Explica el patrón interno del backend (Clean Architecture / Capas: Router → Controller/Service → Repository → Persistence). Inserta un diagrama en sintaxis Mermaid mostrando cliente (móvil/web), API Gateway/Reverse Proxy, Backend Services y Base de Datos.

**Prompt 2:**

> Evalúa adoptar Supabase como plataforma (base de datos, autenticación y almacenamiento de archivos) y registra la decisión en un ADR. Condiciones: el navegador no debe hablar directo con Supabase, la sesión tiene que ser nuestra para que sobreviva días sin conexión, y no quiero quedar atada al proveedor. Compara alternativas y documenta los trade-offs.

### **2.2. Descripción de componentes principales:**

**Prompt 1:**

> *(extracto de la plantilla compartida)* Analiza el stack tecnológico que se seleccionó y cuáles son los compromisos (trade-offs) Frontend: PWA (React/Next.js/Vite) Backend: FastAPI Trade-off principal: priorizar velocidad de carga y funcionamiento offline-first o caché local vs. consistencia estricta en tiempo real.

**Prompt 2:**

> Define dónde vive cada tipo de dato: lo transaccional, lo que el dispositivo necesita para vender sin conexión y los archivos binarios como imágenes de producto (estos últimos, post-MVP). Justifica cada elección y describe tecnología y responsabilidad de cada pieza.

**Prompt 3:**

> Documenta los componentes principales del sistema en una tabla Componente · Tecnología · Responsabilidad, y respalda cada elección importante con un ADR cuyo nombre enuncie la decisión, no solo el tema.

### **2.3. Descripción de alto nivel del proyecto y estructura de ficheros**

**Prompt 1:**

> Propón la estructura de ficheros del monorepo (backend, frontend y configuración) y explica a qué patrón responde. El backend es un monolito modular por capas y el frontend se organiza por funcionalidad. Preséntala como árbol con una tabla del propósito de cada carpeta.

### **2.4. Infraestructura y despliegue**

**Prompt 1:**

> Define la infraestructura y el despliegue de base de datos, backend y frontend en cuatro ambientes: desarrollo, test, staging y producción. Quiero usar Vercel para la PWA y la API y Supabase para la base, en una región cercana a Latinoamérica. Nada debe publicarse sin pasar por CI, y producción requiere aprobación manual. Incluye un diagrama del pipeline y los pasos del despliegue.

**Prompt 2:**

> Documenta el ciclo de trabajo con GitFlow: cómo llega un cambio a `develop`, cómo se hace un release a `master`, cómo se resuelve un hotfix y cómo vuelven los cambios a `develop`. Explica qué tipo de merge conviene en cada caso y por qué.

**Prompt 3:**

> Configura el repositorio de GitHub para este flujo: templates de issues y de PR, un workflow que valide el nombre de las ramas, backport automático y protección de `develop` y `master`. Adáptalo al stack de este proyecto y hazlo mediante un PR, no directo en las ramas protegidas.

### **2.5. Seguridad**

**Prompt 1:**

> Establecer pautas de seguridad que contenga los acuerdos para mantener las dependencias actualizadas para evitar vulnerabilidades, evitar el commit de datos sensibles y evitar las consultas de datos de los clientes, de los tenants de la aplicación.

**Prompt 2:**

> *(extracto de la plantilla compartida)* ¿Cómo se resuelve el aislamiento, autenticación y autorización? Explica el uso de JWT enriquecido con `tenant_id` y `role`. Detalla cómo la capa de backend intercepta cada petición (vía middleware o políticas de Row-Level Security en PostgreSQL) para impedir que un usuario consulte datos de otro comercio, aun manipulando IDs.

### **2.6. Tests**

**Prompt 1:**

> Define la estrategia de tests del MVP. Quiero cubrir unitarios, integración y E2E, con foco en lo crítico: que las ventas sean idempotentes, que el stock no se pierda con ventas concurrentes y que un negocio nunca pueda ver datos de otro. Los tests de integración deben correr contra una base real, no mocks, y todo debe ejecutarse en CI en cada PR. Propón herramientas y ejemplos concretos por nivel.

---

### 3. Modelo de Datos

### **3.1. Diagrama del modelo de datos**

**Prompt 1:**

> *(extracto de la plantilla compartida)* Define las entidades principales y cómo se garantiza el aislamiento multitenant Tenant 1:N Users, Tenant 1:N Products, Tenant 1:N Sales, Sale 1:N SaleItems, Product 1:N SaleItems (congelando precio histórico), Tenant 1:N CashSessions para reportes diarios, y bloqueos para no vender stock negativo ante ventas concurrentes.

**Prompt 2:**

> Genera el diagrama entidad-relación del MVP en Mermaid (`erDiagram`), con claves primarias y foráneas, tipos de cada campo y cardinalidades. Ten en cuenta que es multitenant: toda tabla operativa depende del negocio, y un usuario puede pertenecer a varios negocios con roles distintos.

### **3.2. Descripción de entidades**

**Prompt 1:**

> Describe cada entidad del modelo con el máximo detalle: atributos, tipos, nulabilidad, claves, restricciones y relaciones. Explica también las decisiones que no son obvias, como por qué se guardan precios y costos dentro de cada venta, cómo se evita mezclar datos entre negocios y qué índices hacen falta para vender rápido y sacar reportes por día.

---

### 4. Especificación de la API

**Prompt 1:**

> Especifica en OpenAPI los 3 endpoints principales del MVP: registrar una venta, cerrar una caja y consultar el resumen de ventas y margen. Ten en cuenta que las ventas pueden llegar desde un dispositivo sin conexión y reenviarse, que el negocio sale siempre de la sesión y nunca del request, y que cada rol ve cosas distintas. Incluye un ejemplo de petición y respuesta por endpoint.

---

### 5. Historias de Usuario

**Prompt 1:**

> *(prompt delegado a un subagente, extracto)* Escribe EXACTAMENTE estas 3 historias: registrar una venta rápida incluso sin conexión (cashier), cerrar la caja con arqueo, conocer las ventas y el margen del día (owner). Por historia: "Como… quiero… para…", contexto de negocio, criterios de aceptación en Gherkin en español (camino feliz, sin conexión, permisos por rol, aislamiento entre negocios, casos borde), reglas de negocio, fuera de alcance, dependencias y notas de UX.

---

### 6. Tickets de Trabajo

**Prompt 1:**

> *(prompt delegado a un subagente, extracto)* Escribe 3 tickets, en base a issues del repositorio: Base de datos — políticas RLS, roles y aislamiento (#4); Backend — `POST /api/v1/sales` transaccional e idempotente (#10); Frontend — cola offline de ventas (outbox) con Dexie (#19). Detalla por ticket: metadatos, descripción, alcance técnico, pasos de implementación, criterios de aceptación verificables, tests requeridos, definición de terminado y riesgos.

---

### 7. Pull Requests

Se completa en la Entrega 2, con los primeros PRs de código.
