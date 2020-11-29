# ¿Qué background necesito para poner este proyecto en marcha?
El objetivo es que seas capaz de desplegar esta solución sin tener conocimientos previos de aplicaciones en la nube, Kubernetes o programación.

¿Y si siguiendo las instrucciones no soy capaz? Entonces no hemos conseguido hacer las instrucciones lo suficiéntemente fáciles. Por favor, avísanos para que te intentemos echar una mano y mejoremos la documentación.
[![Twitter URL](https://img.shields.io/twitter/url/https/twitter.com/anaire_co2.svg?style=social&label=Estamos%20para%20ayudar%20%40anaire_co2)](https://twitter.com/anaire_co2)

Te recomendamos que leas este README al completo y que lleves a cabo los pasos enumerados en sección [Instrucciones Paso a Paso](#instrucciones-paso-a-paso).

**Importante** Si vas a utilizar Amazon Web Services consulta la sección de [subvenciones cloud](#subvenciones-cloud) por si pudieses beneficiarte de créditos para hospedar de forma gratuita la solución.

Si tienes experiencia con Kubernetes puedes atreverte con [algunas alternativas](#alternativas) desplegando sobre otra plataforma de tu elección o incluso sobre tu propia máquina física.

# Descripción de la solución Cloud
La solución en la nube consiste en un conjuto de contenedores que se orquestan sobre un cluster Kubernetes.

Nosotros lo hemos orientado como la creación de una máquina virtual que contiene todos los componentes y que ejecutamos en la [nube de Amazon (AWS)](https://aws.amazon.com/). Esto nos da unas ventajas que se enumeran más adelante, pero con unos conocimientos básicos de Kubernetes se podría hacer en cualquier otro hyperscaler (si se desea alojar la solución en la nube) o en un servidor/ordenador/raspberry en el propio colegio/centro en el que se instale la solución.

# Detalle de la solución cloud
## Componentes
En nuestra máquina virtual (o física) instalaremos un cluster Kubernetes (K8s). Dentro de este desplegaremos todos los componentes necesarios para nuestra solución. Estos son:
**Grafana:** Es la interfaz gráfica en la que se pueden consultar los valores de CO2, temperatura y humedad de cada sensor. Obtiene los datoss consultando a Prometheus.
**Prometheus:** Es el encargado de almacenar el histórico de todos los datos recibido por los sensores.
**Pushgateway** Prometheus está pensado para consultar datos, no para que se los envíen. Ahí entra Pushgateway, quien es capaz de recibir los datos de los sensores y presentarlos de forma que Prometheus pueda consultarlos.
**MQTT broker** Mosquitto (MQTT) es un servidor de mensajes ampliamente utilizado en el Internet de las Cosas (IoT). El broker es el servidor de mensajería en el que los dispositivos publicarán las mediciones en el topic 'measurement'. Esta manera de enviar los datos es muy ligera y tiene ventajas adicionales que planteamos incorporar al código en un futuro cercano.
**MQTT forwarder** Se trata de un cliente Mosquitto que se subscribirá al broker para que se notifique cada vez que se reciban nuevas medidas. Este forwarder se encarga de mandar los datos a Pushgateway por HTTP, que es el protocolo que este entiende.
![Componentes Anaire Cloud](https://pbs.twimg.com/media/En763rJXIAAGLH6?format=jpg&name=small)
# Instrucciones paso a Paso
Para entender por qué hemos elegido instalar nuestra solución de esta forma por favor consulta la sección [¿Por qué lo hacemos así?](-#por-que-lo-hacemos-asi-)
## Crear cuenta AWS y configuración básica
## Crear Volumen
## Crear Elastic IP
## Crear Security Group
## Crear imagen base
## Crear Scaling Group
# ¿Por qué lo hacemos así?
## Ventajas
## ¿Cómo funciona un Scaling Group?
## Alternativas
# Instalación en cluster K8s genérico
# Subvenciones Cloud
