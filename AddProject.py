from pm_gn import *
import sys
argv=sys.argv
pgn=ConectarProxmox()
if len(argv)==2:
    if EsUsuario(pgn,argv[1]):
        CrearProyecto(pgn,argv[1])
    elif EsGrupo(pgn,argv[1]):
        for usuario in GetUsuariosGrupo(pgn,argv[1]):
            CrearProyecto(pgn,usuario)
    else:
        print("Usuario/grupo incorrecto.")
else:
    print("Debes indicar el id de un usuario o grupo.")
    print("Usuarios:",GetUsuarios(pgn))
    print("Grupos:",GetGrupos(pgn))
