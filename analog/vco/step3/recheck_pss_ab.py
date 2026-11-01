#!/usr/bin/env python3
import try_pss_bypass_ab as ab

ab.try_pss("bypass_on_recheck", True, npts=8000)
ab.try_pss("bypass_off_recheck", False, npts=8000)
