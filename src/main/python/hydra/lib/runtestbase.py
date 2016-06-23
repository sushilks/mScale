
from hydra.lib.hydrabase import HydraBase


class RunTestBase(HydraBase):
    def __init__(self, test_name, options, config=None,
                 startappserver=True, mock=False, app_dirs=['target', 'src']):
        # I tried unsuccessfully to use **kwargs here
        # May be there is a cleaner way but
        # Anyway this is temporary place holder till we can rename every usages to HydraBase
        HydraBase.__init__(self, test_name, options, config, startappserver, mock, app_dirs)
