# Anaire Cloud
Aplicación en la nube para la visualización de los datos de los dispositivos de Anaire (CO2, temperatura y humedad) y la configuración remota de los dispositivos a través de su conexión a Internet.

- [¿Qué background necesito para poner este proyecto en marcha?](#qu%C3%A9-background-necesito-para-poner-este-proyecto-en-marcha)
- [Descripción de la solución Cloud](#descripci%C3%B3n-de-la-soluci%C3%B3n-cloud)
- [Detalle de la solución cloud](#detalle-de-la-soluci%C3%B3n-cloud)
    - [Componentes](#componentes)
- [Instrucciones paso a Paso](#instrucciones-paso-a-paso)
    - [Crear cuenta AWS y configuración básica](#crear-cuenta-aws-y-configuraci%C3%B3n-b%C3%A1sica)
    - [Crear Volumen](#crear-volumen)
    - [Crear Elastic IP](#crear-elastic-ip)
    - [Crear Security Group](#crear-security-group)
    - [Crear par de claves](#crear-par-de-claves)
    - [Crear imagen base](#crear-imagen-base)
    - [Crear template de VM](#crear-template-de-vm)
    - [Crear Scaling Group](#crear-scaling-group)
- [¿Por qué lo hacemos así?](#por-qu%C3%A9-lo-hacemos-as%C3%AD)
    - [¿Cómo funciona el Scaling Group?](#c%C3%B3mo-funciona-el-scaling-group)
    - [Alternativas](#alternativas)
- [Instalación en cluster K8s genérico](#instalaci%C3%B3n-en-cluster-k8s-gen%C3%A9rico)
- [Subvenciones Cloud](#subvenciones-cloud)
- [¿Cómo revisar el consumo en AWS?](#c%C3%B3mo-revisar-el-consumo-en-aws)

# ¿Qué background necesito para poner este proyecto en marcha?
El objetivo es que seas capaz de desplegar esta solución sin tener conocimientos previos de aplicaciones en la nube, Kubernetes o programación.

¿Y si siguiendo las instrucciones no soy capaz? Entonces no hemos conseguido hacer las instrucciones lo suficiéntemente fáciles. Por favor, avísanos para que te intentemos echar una mano y mejoremos la documentación.
[![Twitter URL](https://img.shields.io/twitter/url/https/twitter.com/anaire_co2.svg?style=social&label=Estamos%20para%20ayudar%20%40anaire_co2)](https://twitter.com/anaire_co2)

Te recomendamos que leas este README al completo y que lleves a cabo los pasos enumerados en sección [Instrucciones Paso a Paso](#instrucciones-paso-a-paso).

**IMPORTANTE** Si vas a utilizar Amazon Web Services consulta la sección de [subvenciones cloud](#subvenciones-cloud) por si pudieses beneficiarte de créditos para hospedar de forma gratuita la solución.

Si tienes experiencia con Kubernetes puedes atreverte con [algunas alternativas](#alternativas) desplegando sobre otra plataforma de tu elección o incluso sobre tu propia máquina física.

# Descripción de la solución Cloud
La solución en la nube consiste en un conjuto de contenedores que se orquestan sobre un cluster Kubernetes.

Nosotros lo hemos orientado como la creación de una máquina virtual que contiene todos los componentes y que ejecutamos en la [nube de Amazon (AWS)](https://aws.amazon.com/). Esto nos da unas ventajas que se enumeran más adelante, pero con unos conocimientos básicos de Kubernetes se podría hacer en cualquier otro hyperscaler (si se desea alojar la solución en la nube) o en un servidor/ordenador/raspberry en el propio colegio/centro en el que se instale la solución.

¿No tienes claro qué son los contenedores? En este vídeo explicamos qué son los contenedores, Kubernetes y Helm, que son las tecnologías en las que se basa el despliegue de nuestra aplicación.

[![Contenedores, Kubernetes y Helm](http://img.youtube.com/vi/WFg_gGl5aIU/0.jpg)](https://youtu.be/WFg_gGl5aIU)

# Detalle de la solución cloud
## Componentes
En nuestra máquina virtual (o física) instalaremos un cluster Kubernetes (K8s). Dentro de este desplegaremos todos los componentes necesarios para nuestra solución. Estos son:
* **Grafana:** Es la interfaz gráfica en la que se pueden consultar los valores de CO2, temperatura y humedad de cada sensor. Obtiene los datos consultando a Prometheus.
* **Prometheus:** Es el encargado de almacenar el histórico de todos los datos recibido por los sensores.
* **Pushgateway:** Prometheus está pensado para consultar datos, no para que se los envíen. Ahí entra Pushgateway, quien es capaz de recibir los datos de los sensores y presentarlos de forma que Prometheus pueda consultarlos.
* **Pushgateway cleaner:** Se trata de un cronjob, es decir, un proceso que se arranca periódicamente, se ejecuta y desaparece. Se utiliza para eliminar las entradas de Pushgateway de aquellos dispositivos que hace más de 5 minutos que no están generando datos.
* **MQTT broker:** Mosquitto (MQTT) es un servidor de mensajes ampliamente utilizado en el Internet de las Cosas (IoT). El broker es el servidor de mensajería en el que los dispositivos publicarán las mediciones en el topic 'measurement'. Esta manera de enviar los datos es muy ligera y tiene ventajas adicionales que planteamos incorporar al código en un futuro cercano.
* **MQTT forwarder:** Se trata de un cliente Mosquitto que se subscribirá al broker para que se notifique cada vez que se reciban nuevas medidas. Este forwarder se encarga de mandar los datos a Pushgateway por HTTP, que es el protocolo que este entiende.
* **API server:** Se trata de una API rest que utilizamos para inyectar configuraciones a los dispositivos desde Grafana. Grafana invoca esta API que se encarga de traducir a mensajes MQTT que los dispositivos reciben.
![Componentes Anaire Cloud](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/componentes.jpg)
# Instrucciones paso a Paso
Para entender por qué hemos elegido instalar nuestra solución de esta forma por favor consulta la sección [¿Por qué lo hacemos así?](#por-qué-lo-hacemos-así)

En estas instrucciones vamos a desplegar sobre AWS, pero el despliegue de la aplicación en sí es con un Helm Chart, así que cualquier entorno de Kubernetes, ya sea en un proveedor de cloud o en una máquina de vuestra propiedad valdría.

**IMPORTANTE:** En los pasos siguientes se va a crear una cuenta en Amazon Web Services y desplegar recursos sobre esta. Desplegar recursos tiene un coste asociado que se factura mensualmente. Estas instrucciones están pensadas para desplegar la solución con un coste mínimo, pero es IMPRESCINDIBLE mantener una monitorización de cuánto consumo se está haciendo para no llevarnos un susto con la factura a fin de mes. Estas instrucciones no garantizan el importe de la factura.

**IMPORTANTE** Asegurate de mantener tus credenciales de la cuenta AWS en lugar seguro y de impedir que nadie tenga acceso a tu VM. Si alguien tiene acceso a tus credenciales podría desplegar recursos incrementando tu factura.

**IMPORTANTE** Intentamos crear unas instrucciones todo lo detalladas que podemos y estaremos encantados de intentarte ayudar a arrancar tu copia de este software, pero no podemos hacernos responsables del consumo ni de la seguridad de tu cuenta en Amazon Web Services ni en ningún otro proveedor cloud. En caso de no estar seguro de ser capaz de poder controlar estos aspectos por tí mismo pide ayuda a alguien con experiencia de despliegues cloud.

## Crear cuenta AWS y configuración básica
[Crea una nueva cuenta](https://portal.aws.amazon.com/billing/signup#/start)
Rellena la información de contacto solicitada y la información de pago.

Esto te proporcionará un usuario raiz. Es una mala práctica usar el usuario raiz para crear recursos. En su lugar crearemos un usuario IAM.
1. [Inicia sesión en la consola](https://console.aws.amazon.com/console/home?nc2=h_ct&src=header-signin) como usuario raíz con los datos que acabas de obtener
2. En la barra de búsqueda de servicios busca IAM y accede a este servicio.
3. En el menú de la izquierda pulsa sobre 'Usuarios'
4. Pulsa el botón 'Añadir usuario(s)'
5. Selecciona nombre de usuario y marca las opciones 'Acceso mediante programación' y 'Acceso a la consola de administración de AWS'
El 'Acceso mediante programación' proporionará las credenciales para que más tarde seamos capaces de gestionar nuestra cuenta mediante un script.
el 'Acceso a la consola de administración de AWS' nos proporcionará un usuario y contraseña que usar en lugar del usuario raiz.
Si lo deseas puedes elegir qué contraseña quieres y si en el próximo login será necesario cambiarla
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/crear_usuario_1.jpg)
Y pulsa 'Siguiente'
6. Selecciona el grupo 'admin' para proporcionar acceso a todos los recursos
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/crear_usuario_2.jpg)
Y pulsa 'Siguiente'
7. Añade alguna etiqueta si lo deseas y pulsa 'siguiente'
8. Revisa la información y pulsa 'Crear un usuario'

Deberías ver una ventana de confirmación con este aspecto. Descarga el archivo CSV y asegurate de dejarlo almacenado en un sitio seguro. El usuario creado tiene permisos de administrador y por tanto puede crer todos los recursos que quiera, lo que podría suponer una factura considerable.
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/crear_usuario_3.jpg)

En el archivo descargado deberías tener los campos "User name,Password,Access key ID,Secret access key,Console login link"
* **User name:** Nombre del usario IAM
* **Password:** Contraseña asignada al usuario IAM
* **Access key ID:** ID que se debe utilizar en el script para permitir al mismo crear recursos en AWS.
* **Secret access key:** Contraseña que se debe usar junto al 'Access key ID' en el script para permitir al mismo crear recursos en AWS
* **Console login link:** Enlace directo para hacer login. El ID de 12 dígitos con el que comienza es el ID de cuenta.

A partir de ahora este será el usuario que utilicemos para crear los recursos y no el usuario raíz.

## Crear Volumen
1. [Inicia sesión en la consola](https://console.aws.amazon.com/console/home?nc2=h_ct&src=header-signin) con ID de cuenta y tu usuario IAM creado en [la sección anterior](#crear-cuenta-aws-y-configuración-básica)
2. En la parte superior derecha se puede seleccionar dónde se quieren crear los recursos. Irlanda es la zona en Europa donde más barato resulta desplegar recursos, te recomendamos esta opción.
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/volumen_1.jpg)
3. En buscar servicios selecciona 'EC2'
4. En el menú lateral izquierdo, en la sección 'Elastic Block Storage' selecciona Volúmenes
5. Pulsa el botón 'Create Volume'
6. Selecciona 'General Purpose SSD (gp2)' y 'Size (GiB)' 5. La availability zone puede ser la que prefieras, pero recuerda en qué Availability Zone (AZ) creas el volumen puesto que la máquina virtual (VM) debe crearse en la misma AZ.
7. Ahora deberías tener un volumen con state 'available'
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/volumen_2.jpg)
Apunta el 'Volume ID', es el identificador que más adelante tendremos que indicar en el script para asociar nuestra máquina virtual a este volumen.

## Crear Elastic IP
1. Asumiendo que acabas de terminar la sección anterior, en el menú lateral izquierdo selecciona 'Direcciones IP elásticas' dentro de la sección 'Red y seguridad'.
2. Pulsa el botón 'Asignar la dirección IP elástica'
3. Deja la selección por defecto 'Grupo de direcciones IPv4 de Amazon' y pulsa el botón asignar.
4. Deberías llegar a una pantalla como la siguiente:
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/eip_1.jpg)
Apunta tanto la 'Dirección IPv4 asignada' como el 'ID de asignación'. La primera es la IP que usaremos para poder consultar la interfaz gráfica y a la que los dispositivos mandarán las mediciones. La segunda es el identificador que más adelante tendremos que indicar en el script para asociar nuestra máquina virtual a esta IP.

## Crear Security Group
1. Asumiendo que acabas de terminar la sección anterior, en el menú lateral izquierdo selecciona 'Security Groups' dentro de la sección 'Red y seguridad'.
2. Pulsa el botón 'Crear grupo de seguridad'
3. Rellena un nombre y una descripción. En VPC te aparecerá la VPC por defecto. A menos que estés usando una cuenta AWS en la que hayas creado VPCs adicionales y quieras usar una de éstas, no lo toques.
4. Añade las siguientes reglas de entrada:
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/security_group_1.jpg)
NOTA: Sólo estamos permitiendo comunicación con el puerto que usará el broker MQTT y con el puerto que usaremos para consultar Grafana. No estamos permitiendo SSH pues eso haría nuestra máquina más vulnerable. Si fuese necesario hacer troubleshooting se habilitaría el SSH sólo desde la IP que estemos usando (esto estará descrito más adelante en una sección de troubleshooting).
5. Mantén las reglas de salida como están (permitiendo todo el tráfico).
6. Pulsa el botón 'Crear grupo de seguridad'

## Crear par de claves
1. Asumiendo que acabas de terminar la sección anterior, en el menú lateral izquierdo selecciona 'Par de claves' dentro de la sección 'Red y seguridad'.
2. Pulsa el botón 'Crear par de claves'
3. Escribe un nombre para el par de claves
4. Selecciona el formato deseado del archivo. Tipicamente será 'pem', pero si tu intencción es usar PuTTy para conectar con la máquina selecciona 'ppk'.
5. Pulsa 'Crear par de claves'. Al hacerlo se descargará automáticamente tu clave privada. Guárdala en lugar seguro porque será la forma de acceder a tu máquina virtual.

## Crear un rol IAM
1. En la barra de búsqueda de servicios busca IAM y accede a este servicio.
2. Pulsa en la columna 'Roles'
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/roles_1.jpg)
3. Selecciona caso de uso 'EC2' y pulsa siguientes
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/roles_2.jpg)
4. Busca y selecciona la política 'AmazonEC2FullAccess' y pulsa siguiente.
![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/roles_3.jpg)
5. El uso de etiquetas es opcional. Indica alguna si lo consideras necesario y pulsa siguiente.
6. Indica un nombre de rol descriptivo, como por ejemplo 'AmazonEC2FullAccess' y pulsa 'Crear un rol'

En este punto tenemos:
* Un volumen preparado para almacenar los datos de nuestras aplicaciones
* Una IP elástica, que será la IP que usarán tanto nuestros dispositivos para enviar los datos como nosotros para acceder a la interfaz gráfica
* Un par de claves para acceder a la máquina que crearemos para hospedar nuestra aplicación
* Un security Group
* Un rol IAM

## Crear template de VM
1. En el menú laterar de EC2, ve a 'Plantillas de lanzamiento' dentro de la sección 'Instancias'
2. Pulsa el botón 'Crear plantilla de lanzamiento'
3. Da un nombre a la plantilla
4. Selecciona como 'Imagen de Amazon Machine (AMI)' la imagen Ubuntu Minimal 20.04
5. Selecciona t3a.medium como 'Tipo de instancia'. Si se usa un tamaño menor será necesaro ajustar las variables del helm chart puesto que está ajustado para una máquina de 2CPU y 4GiB
6. Selecciona el par de claves que creamos anteriormente
7. Abre el desplegable 'Detalles avanzados'
8. En "Perfil de instancia de IAM" seleccional el rol IAM que hemos creado anteriormente
9. Desplázate hasta el final de la página donde se encuentra la caja 'Datos de usuario'
En esta caja tienes que copiar el contenido del [userdata preparado en nuestro github](https://github.com/anaireorg/anaire-cloud/blob/main/stack/user_data_aws_scaling_group_ready.sh). Actualiza las variables de las secciones 'AWS variables' y 'Stack Variables' antes de crear el template

## Crear Scaling Group
Ahora crearemos un scaling group que contendrá una sola VM. Este se basará en el template que acabamos de crear y que se encarga de cada vez que la vm se arranque enlazarla con el volumen, con la IP elástica y volver a arrancar las aplicaciones.

1. En el menú laterar de EC2, ve a 'Grupos de Auto Scaling' dentro de la sección 'Auto Scaling'.
2. Pulsa el botón Crear grupo de Auto Scaling
3. Elige nombre y selecciona la plantilla que hemos creado. Pulsa siguiente.
4. En la sección 'Red', en el apartado 'Subredes' selecciona únicamente la subred correspondiente a la Availability Zone en la que creaste el volumen anteriormente
5. Pulsa siguiente dejando los parámetros por defecto hasta que llegues a la pantalla 'Configurar políticas de escalado y tamaño de grupo', en donde debes asegurarte de que en la sección 'Tamaño del grupo' están puesto a 1 los parámetros 'Capacidad deseada', 'Capacidad mínima' y 'Capacidad máxima'
6. Continua pulsando siguiente hasta llegar a la pantalla 'Revisar'
6. Pulsa el botón 'Crear grupo de Auto Scaling'

### ¿Por qué lo hacemos así?
AWS, al igual que el resto de hyperscalers tienen servicios de Kubernetes gestionados que ofrecen alta disponibilidad y te ocultan la complejidad de la gestión del cluster. Pese a ello, la aproximación seguida aquí, en la que no se utilizan los servicios gestionados de Kubernetes, tiene las siguientes ventajas:
* Ejecutar en un hyperscaler (AWS en este caso) permite
    * Tener acceso a los datos a través de Internet desde cualquier ubicación
    * Reduce la probabilidad de que falle la VM
    * Posibilidad de uso de Scaling Group, maximizando la resiliencia de la solución
* Ejecutar en una VM autocontenida permite
    * Minimizar el coste
    * Poder migrar la solución fácilmente a otra plataforma
    * Ampliar el setup incluyendo una segunda VM autocontenida que sean copia una de otra sería relativamente sencillo haciendo que los broker MQTT funcionasen como cluster

### ¿Cómo funciona el Scaling Group?
Básicamente el scaling group lo que hace es monitorizar en número de instancias que tienes en el grupo y asegurarse de que siempre se esté en el número deseado de instancias.

En nuestro caso el número deseado es 1, y en el template hemos hecho que esa instancia esté ligada a nuestro volumen y a nuestra elastic IP. Esto consigue que si la VM es terminada, ya sea porque por error la borramos o porque hay un fallo catastrófico en AWS que provoca que la VM muera, otra VM la reemplazaría, pero con la misma IP y con los mismos datos almacenados, por lo que a todos los efectos sería como si no hubiese fallado.

En nuestra experiencia el tiempo que tarda la nueva máquina virtual en estar accesible prestando servicio es entre 5 y 10 minutos desde que se borra la VM original.

![image](https://github.com/anaireorg/anaire-cloud/raw/main/screenshots/scaling_group.jpg)

# Alternativas
Realmente la aplicación no tiene requisitos especiales, sólo necesita un cluster Kubernetes y crear el directorio /data, que es donde se almacenan los datos persistentes.
Podría utilizarse hospedaje para la VM en cualquier otro hyperscaler, usar un servicio de Kubernetes gestionado o instalar el cluster Kubernetes en un equipo físico dentro del centro (colegio) a monitorizar.

# Instalación en cluster K8s genérico
Toda la aplicación se despliega mediante un Helm Chart que está en [el directorio stack de Github](https://github.com/anaireorg/anaire-cloud/tree/main/stack/anairecloud).

El fichero values permite adaptar el tamaño de los contenedores y seleccionar si se quiere TLS, en qué nombre de dominio o IP estará accesible grafana y el MQTT, y cuál es la contraseña que queremos poner al usuario administrador de Grafana.

Para empezar a familiarizarse con el entorno sugerimos instalar con:
helm install --set tls=false --set publicIP=<IP de vuestra máquina> --set grafanaAdminPass=<contraseña para grafana> anairestack anaire-cloud/stack/anairecloud
(el último campo es el path del helm chart)

# Virtualbox
Aún no está disponible pero nuestra intención es proporcionar una imagen de Virtualbox para que podáis simplemente arrancarla en un PC y que ahí esté toda la aplicacion.
Aún es un trabajo en curso, pero lo que estamos haciendo es básicamente instalar una Ubuntu Minimal 20.04 (es la minimal por que ocupe lo menos posible, podría ser la versión completa) y instalamos sobre ella microk8s y la aplicación con el [este script](https://github.com/anaireorg/anaire-cloud/blob/main/stack/user_data.sh) (importante asegurarse de que PUBLIC_IP y GRAFANA_ADMIN_PASSWORD tienen los valores que queremos).

Si te animas a usar esta opción nos gustaría que nos hicieses llegar como te ha ido. Creemos que colgar en internet la imagen de Virtualbox para que sea plug&play será cómodo para muchos usuarios, pero si instaláis el sistema operativo y ejecutáis el script sería los mismo.

# Subvenciones Cloud
Comprueba si gracias a alguno de estos programas podrías obtener créditos para correr la aplicación de forma gratuita.
* [Open data sponsorship program](https://aws.amazon.com/es/opendata/open-data-sponsorship-program/)
* [AWS Educate](https://aws.amazon.com/es/education/awseducate/)

# Cómo revisar el consumo en AWS
Accede a la sección de Billing para tener acceso al consumo actual y a una predicción del consumo esperado a fin de mes.
Por defecto los usuarios administradores no tienen acceso completo al billing. Puedes conceder estos permisos siguiendo la documentación de AWS o usar el usuario raiz para realizar estas consultas.
