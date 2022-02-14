from pm_gn import *
import sys
argv=sys.argv
pgn=ConectarProxmox()
if len(argv)!=2:
    print("Debes indicar el id de un usuario o grupo.")
elif len(argv)==2:
    if EsUsuario(pgn,argv[1]):
        resp=input("Indica el id del tamplate a clonar:")
        name=input("Nombre de la nueva máquina:")
        ClonarMV(pgn,resp,name,argv[1])
            
    elif EsGrupo(pgn,argv[1]):
        resp=input("Indica el id del tamplate a clonar:")
        name=input("Nombre de la nueva máquina:")
        for usuario in GetUsuariosGrupo(pgn,argv[1]):
            ClonarMV(pgn,resp,name,usuario)
    else:
        print("Debes indicar el id de un usuario o grupo.")
        print("Usuarios:",GetUsuarios(pgn))
        print("Grupos:",GetGrupos(pgn))