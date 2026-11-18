Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\backup_calegari_projetos\Microsite_Pedidos_Backup_20261015\site_sublimacao"
WshShell.Run """C:\Users\criac\AppData\Local\Programs\Python\Python314\pythonw.exe"" ""D:\backup_calegari_projetos\Microsite_Pedidos_Backup_20261015\site_sublimacao\servidor_impressao.py""", 0, False
