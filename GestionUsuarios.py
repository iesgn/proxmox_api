from pm_gn import *
import sys
argv=sys.argv
pgn=ConectarProxmox()
if len(argv)==2:
    if EsUsuario(pgn,argv[1]):
        resp=input("¿Activar (a) o desactivar (d)?")
        if resp=="a":
            ActivarUsuario(pgn,argv[1],1)
        elif resp=="d":
            ActivarUsuario(pgn,argv[1],0)
    elif EsGrupo(pgn,argv[1]):
        resp=input("¿Activar (a) o desactivar (d)?")
        for usuario in GetUsuariosGrupo(pgn,argv[1]):
            if resp=="a":
                ActivarUsuario(pgn,usuario,1)
            elif resp=="d":
                ActivarUsuario(pgn,usuario,0)
    else:
        print("Usuario/grupo incorrecto.")
else:
    print("Debes indicar el id de un usuario o grupo")
    print("Usuarios:",GetUsuarios(pgn))
    print("Grupos:",GetGrupos(pgn))
