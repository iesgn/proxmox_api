from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException
import os
import sys
import time


class color:
   PURPLE = '\033[1;35;48m'
   CYAN = '\033[1;36;48m'
   BOLD = '\033[1;37;48m'
   BLUE = '\033[1;34;48m'
   GREEN = '\033[1;32;48m'
   YELLOW = '\033[1;33;48m'
   RED = '\033[1;31;48m'
   BLACK = '\033[1;30;48m'
   UNDERLINE = '\033[4;37;48m'
   END = '\033[1;37;0m'

def alert(text):
    print(color.RED + text + color.END)

def warning(text):
    print(color.BLUE + text + color.END)

# Storages que se asignan a cada proyecto. Los que no existan en el Proxmox se ignoran.
STORAGE=["local","local-lvm","remoto-lvm"]
def ConectarProxmox():
    try:
        # Por defecto se entra por el proxy inverso (puerto 443, certificado válido).
        # Para ir directo a un nodo (8006, certificado autofirmado): PM_PORT=8006 y PM_VERIFY_SSL=no
        proxmox = ProxmoxAPI(os.environ['PM_SERVER'], port=int(os.environ.get('PM_PORT','443')),
                             user=os.environ['PM_USERNAME']+"@"+os.environ['PM_REALM'],password=os.environ['PM_PASSWORD'],
                             verify_ssl=os.environ.get('PM_VERIFY_SSL','si')!="no")
        proxmox.version.get()
    except KeyError as e:
        print("Falta la variable de entorno %s (¿has hecho source openrc?)." % e)
        sys.exit(1)
    except Exception as e:
        print("Problemas a conectar con el servidor Proxmox Gonzalo Nazareno:", e)
        sys.exit(1)
    return proxmox

def GetUsuarios(pm):
    return [user["userid"] for user in pm.access.users.get()]

def EsUsuario(pm,id):
    return id in GetUsuarios(pm)

def GetGrupos(pm):
    return [group["groupid"] for group in pm.access.groups.get()]

def EsGrupo(pm,idg):
    return idg in GetGrupos(pm)

def GetUsuariosGrupo(pm,idg):
    return pm.access.groups(idg).get().get("members",[])

def EsUsuarioGrupo(pm,id,idg):
    return id in GetUsuariosGrupo(pm,idg)

def NombreProyecto(id):
    return "Proyecto_"+id.replace("@","_")

def ExisteProyecto(pm,newid):
    return newid in [pool["poolid"] for pool in pm.pools.get()]

def GetStorages(pm):
    return [stor["storage"] for stor in pm.storage.get()]

def GetStorageProyecto(pm,newid):
    return [miembro["storage"] for miembro in pm.pools(newid).get()["members"] if miembro["type"]=="storage"]

def AsignarStorageProyecto(pm,newid):
    existentes=GetStorages(pm)
    actuales=GetStorageProyecto(pm,newid)
    for stor in STORAGE:
        if stor in existentes and stor not in actuales:
            pm.pools(newid).set(storage=stor)
            print("Añadiendo storage:",stor)

def CrearProyecto(pm,id):
    newid=NombreProyecto(id)
    try:
        if ExisteProyecto(pm,newid):
            print(newid,"ya existe...")
        else:
            pm.pools.create(poolid=newid)
            print(newid,"creado...")
        AsignarStorageProyecto(pm,newid)
        pm.access.acl.set(path="/pool/"+newid,roles="iesgn",users=id)
    except ResourceException as e:
        alert("Problemas al crear el proyecto %s: %s" % (newid,e))

def UpdateProyectoStorage(pm,id):
    newid=NombreProyecto(id)
    try:
        AsignarStorageProyecto(pm,newid)
        print(newid,"modificado...")
    except ResourceException as e:
        alert("Problemas al modificar el proyecto %s: %s" % (newid,e))

def GetVMProyecto(pm,id):
    newid=NombreProyecto(id)
    try:
        return [miembro["id"] for miembro in pm.pools(newid).get()["members"] if miembro["type"] in ("qemu","lxc")]
    except ResourceException:
        return []

# Devuelve la entrada de cluster/resources de una MV/CT (node, type, name, status...)
def GetRecursoMV(pm,vmid):
    for recurso in pm.cluster.resources.get(type="vm"):
        if recurso["vmid"]==int(vmid):
            return recurso
    return None

def GetMV(pm,recurso):
    return pm.nodes(recurso["node"])(recurso["type"])(recurso["vmid"])

def EsperarTarea(pm,node,upid):
    while True:
        estado=pm.nodes(node).tasks(upid).status.get()
        if estado["status"]=="stopped":
            return estado.get("exitstatus")=="OK"
        time.sleep(2)

def InfoVM(pm,mv):
    info=GetRecursoMV(pm,mv.split("/")[1])
    text=mv
    espacios=" "*(20-len(info.get("name","")))
    text+="\t"+info.get("name","")+espacios+str(info["maxcpu"])+" - "+str(int(info["maxmem"]/1024/1024))+" - "+str(int(info["maxdisk"]/1024/1024/1024))+"\t"+info["status"]
    return text

# Para (si hace falta) y elimina una MV o CT. Al eliminarla, Proxmox la quita también del pool.
def EliminarMV(pm,mv):
    recurso=GetRecursoMV(pm,mv.split("/")[1])
    if recurso is None:
        alert("No se encuentra la máquina %s." % mv)
        return False
    maquina=GetMV(pm,recurso)
    try:
        if maquina.status.current.get()["status"]!="stopped":
            maquina.status.stop.create()
            while maquina.status.current.get()["status"]!="stopped":
                time.sleep(2)
                print("Parando...",mv)
        if not EsperarTarea(pm,recurso["node"],maquina.delete(purge=1)):
            alert("Error al eliminar la máquina %s (ver el log de tareas de Proxmox)." % mv)
            return False
        print("Eliminando mv:",mv)
        return True
    except ResourceException as e:
        alert("Error al eliminar la máquina %s: %s" % (mv,e))
        return False

def EliminarProyectoMV(pm,id):
    todas=True
    for mv in GetVMProyecto(pm,id):
        if not EliminarMV(pm,mv):
            todas=False
    return todas

def EliminarProyecto(pm,id):
    newid=NombreProyecto(id)
    if not ExisteProyecto(pm,newid):
        print(newid,"no existe...")
        return
    if not EliminarProyectoMV(pm,id):
        alert("No se elimina el proyecto %s porque quedan máquinas." % newid)
        return
    try:
        for stor in GetStorageProyecto(pm,newid):
            pm.pools(newid).set(storage=stor,delete=1)
            print("Eliminando storage:",stor)
        pm.pools(newid).delete()
        print(newid,"eliminado...")
    except ResourceException as e:
        alert("Problemas al eliminar el proyecto %s: %s" % (newid,e))


def ActivarUsuario(pm,id,op):
    try:
        pm.access.users(id).set(enable=op)
        print("Cambiado con éxito el usuario:", id)
    except ResourceException as e:
        alert("Problemas al procesar el usuario %s: %s" % (id,e))


def PermisoUsuarioProyecto(pm,id,proy,op):
    newid=NombreProyecto(proy)
    try:
        if op==1:
            pm.access.acl.set(path="/pool/"+newid,roles="iesgn",users=id)
            print("Concediendo permisos de %s a %s" % (newid,id))
        if op==0:
            pm.access.acl.set(path="/pool/"+newid,roles="iesgn",users=id,delete=1)
            print("Quitando permisos de %s a %s" % (newid,id))
    except ResourceException as e:
        alert("Problemas al gestionar %s - %s: %s" % (newid,id,e))


def NewIdMV(pm):
    return int(pm.cluster.nextid.get())


# Clona una plantilla (MV o CT) en el proyecto del usuario. Espera a que termine
# el clonado para que el siguiente NewIdMV no devuelva el mismo id.
def ClonarMV(pm,id,name,user):
    pool=NombreProyecto(user)
    recurso=GetRecursoMV(pm,id)
    if recurso is None:
        alert("No existe la plantilla %s." % id)
        return
    try:
        newid=NewIdMV(pm)
        if recurso["type"]=="qemu":
            upid=GetMV(pm,recurso).clone.create(newid=newid,name=name,pool=pool)
        else:
            upid=GetMV(pm,recurso).clone.create(newid=newid,hostname=name,pool=pool)
        if EsperarTarea(pm,recurso["node"],upid):
            print("Clonada %s en %s (id %d)" % (id,pool,newid))
        else:
            alert("Error al clonar %s en %s (ver el log de tareas de Proxmox)." % (id,pool))
    except ResourceException as e:
        alert("Problemas al clonar MV %s: %s" % (id,e))
