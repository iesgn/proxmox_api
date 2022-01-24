from ast import In
from pm_gn import *
import sys


def ListMv(pgn,usuario):
    vms=GetVMProyecto(pgn,usuario)
    if len(vms)>0:
        warning(usuario)
        for vm in vms:
            alert(InfoVM(pgn,vm))
        warning("."*80)
        print()

argv=sys.argv
pgn=ConectarProxmox()
if len(argv)==2:
    if EsUsuario(pgn,argv[1]):
        ListMv(pgn,argv[1])
    elif EsGrupo(pgn,argv[1]):
        for usuario in GetUsuariosGrupo(pgn,argv[1]):
            ListMv(pgn,usuario)
            
        
        print
    else:
        print("Usuario/grupo incorrecto.")
else:
    print("Debes indicar el id de un usuario o grupo")
    print("Usuarios:",GetUsuarios(pgn))
    print("Grupos:",GetGrupos(pgn))
