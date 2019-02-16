set PYTHONPATH=.\Test;.\plexee.plexforboxee
cd ..
mkdir .\Tests\OUT 
c:\python24\python .\Tests\test_util.py 1>.\Tests\OUT\test_out.log 2>.\Tests\OUT\test_out_err.log
c:\python24\python .\Tests\test_plex.py 1>>.\Tests\OUT\test_out.log 2>>.\Tests\OUT\test_out_err.log
c:\python24\python .\Tests\test_plexee.py 1>>.\Tests\OUT\test_out.log 2>>.\Tests\OUT\test_out_err.log
c:\python24\python .\Tests\test_listener.py 1>>.\Tests\OUT\test_out.log 2>>.\Tests\OUT\test_out_err.log