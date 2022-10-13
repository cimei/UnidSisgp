# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['app.py'],
             pathex=['C:\\Users\\cimeibt\\Documents\\PythonScripts\\UnidSisgp'],
             binaries=[],
             datas=[('instance','var\\project-instance'),
                    ('project\\core', 'project\\core'),
                    ('project\\demandas', 'project\\demandas'),
                    ('project\\error_pages', 'project\\error_pages'),
                    ('project\\objetos', 'project\\objetos'),
                    ('project\\pgs', 'project\\pgs'),
                    ('project\\static','project\\static'),
                    ('project\\templates', 'project\\templates'),
                    ('project\\usuarios', 'project\\usuarios')],
             hiddenimports=['sqlalchemy.sql.default_comparator','pyodbc'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='app',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )