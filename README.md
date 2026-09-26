# proxmox_api
Aplicaciones python que usan la librería [proxmoxer](https://github.com/proxmoxer/proxmoxer) para la gestión de la API de proxmox en el IES Gonzalo Nazareno

La documentación de la configuración (roles, pools y redes) está en el repositorio `infra_iesgn`: `proxmox/roles.md` y `proxmox/redes.md`.

## Instalación

Los scripts trabajan a través de la API, así que se pueden ejecutar desde cualquier máquina con acceso al servidor (no hace falta hacerlo en el nodo).

```
git clone git@github.com:iesgn/proxmox_api.git
cd proxmox_api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp example_openrc openrc
```

En `openrc` se indican el usuario, el realm y el servidor. La contraseña se pide al cargarlo:

```
export PM_USERNAME=admin
export PM_REALM=pve
...
export PM_SERVER="proxmox.gonzalonazareno.org"
```

Por defecto se conecta al puerto **443** (el proxy inverso de `proxmox.gonzalonazareno.org`, con certificado válido) y **verifica el certificado SSL**. Para conectar directamente a un nodo (puerto 8006, certificado autofirmado) hay dos variables opcionales:

```
export PM_PORT=8006
export PM_VERIFY_SSL=no
```

Antes de usar los scripts:

```
source openrc
```

Si el usuario o la contraseña no son correctos, el script se para al conectar.

## Convenciones

* El argumento de la mayoría de los scripts es un **usuario** (`usuario@iesgn`) o un **grupo** (`asir1-iesgn`). Si es un grupo, se procesan todos sus miembros. Sin argumento, se muestran los usuarios y grupos que existen.
* El pool (proyecto) de cada usuario se llama `Proyecto_` + el usuario con `@` cambiado por `_`: `Proyecto_ana_iesgn`.
* El nodo donde está cada máquina se obtiene de la API (`cluster/resources`), no está fijado en el código.
* Los scripts que crean cosas son idempotentes: lo que ya existe no se toca, y se pueden volver a ejecutar.

## Scripts de proyectos y máquinas

| Script | Qué hace |
|---|---|
| `CreateRolesIesgn.py` | Crea (o actualiza a los privilegios de la lista) los roles `iesgn`, `iesgn-red`, `iesgn-template-clone`, `iesgn-template-create` e `iesgn-bridge`. Crea el pool `Imagenes` y asigna `iesgn-template-clone` sobre él a todos los grupos `*-iesgn`, y `iesgn-template-create` a `profesores-iesgn` |
| `AddProject.py <usuario\|grupo>` | Crea el pool del usuario, le añade los storages `local`, `local-lvm` y `remoto-lvm` (los que no existan se ignoran) y le da al usuario el rol `iesgn` sobre él. Si el pool ya existe, completa lo que le falte |
| `UpdateProjectStorage.py <usuario\|grupo>` | Añade a los pools los storages de la lista que les falten |
| `ListProyectos.py <usuario\|grupo>` | Lista las MV y CT de cada proyecto: nombre, CPUs, RAM (MB), disco (GB) y estado |
| `CloneMV.py <usuario\|grupo>` | Pide el id de una plantilla (MV o CT) y un nombre, y la clona en el proyecto de cada usuario. Espera a que termine cada clonado |
| `DeleteProjectMV.py <usuario\|grupo>` | Para y borra (con `purge`) todas las MV y CT de los proyectos. Pide confirmación |
| `DeleteProject.py <usuario\|grupo>` | Igual, y además quita los storages y borra el pool. Si alguna máquina no se puede borrar, el pool se mantiene. Pide confirmación |
| `GestionUsuarios.py <usuario\|grupo>` | Activa o desactiva usuarios |
| `ModificarUsarioProyecto.py <usuario> <usuario\|grupo>` | Da o quita al primer usuario el rol `iesgn` sobre los proyectos del segundo usuario o de todos los usuarios del grupo |

## Scripts de redes por usuario (SDN)

Cada usuario tiene tres VNets propias (`vmbr100`, `vmbr101`...) en la zona SDN `proyecto`, con alias `<usuario> <grupo> red<N>`. El diseño completo está en `infra_iesgn/proxmox/redes.md`. Todos aceptan `--dry-run`, que muestra lo que harían sin cambiar nada.

| Script | Qué hace |
|---|---|
| `CreateZonaProyecto.py` | Crea la zona Simple `proyecto` y aplica el SDN |
| `AddRedesProyecto.py <grupo> [--dry-run]` | Crea las 3 VNets que le falten a cada usuario del grupo (un usuario nuevo recibe tres números seguidos libres) y le da el rol `iesgn-bridge` sobre ellas. No usa nombres que existan como interfaz en algún nodo ni que aparezcan en la configuración de alguna MV/CT. Aplica el SDN solo si ha creado algo |
| `PermisosLocalnetwork.py <grupo> [--dry-run]` | Pone al grupo `NoAccess` sobre `vmbr1`, que queda solo para `admin`. Si es un grupo de alumnos, además le da `iesgn-bridge` sobre `vmbr0` y le quita `iesgn-red` sobre la zona `localnetwork`. Con `profesores-iesgn` mantiene su `iesgn-red` |
| `DeleteRedesProyecto.py <usuario\|grupo> [--huerfanas] [--dry-run]` | Borra las VNets del usuario o de los usuarios del grupo, y sus ACLs. Con `--huerfanas` (se puede usar solo) borra también las VNets cuyo usuario ya no existe. No borra las VNets que usa alguna MV/CT. Pide confirmación |

Las constantes de la configuración de redes (nombre de la zona, número de redes por usuario, rol, bridges compartidos y rango de nombres) están al principio de la sección de redes de `pm_gn.py`.

## Orden de uso

Al principio de curso:

```
python3 CreateRolesIesgn.py
python3 CreateZonaProyecto.py
python3 AddProject.py <grupo>
python3 AddRedesProyecto.py <grupo>
python3 PermisosLocalnetwork.py <grupo>     # solo grupos de alumnos
```

Al final de curso:

```
python3 DeleteProject.py <grupo>
python3 DeleteRedesProyecto.py <grupo>
```
