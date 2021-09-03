#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
import subprocess

w = 200
h = 130
areas = [
        (1341, 323),
        (1545, 318),
        (1341, 450),
        (1545, 451),
        (1341, 580),
        (1545, 582),
        (1341, 708),
        (1545, 714),
        ]

main_idx = 0
for input_file in sorted(os.listdir('.')):
    if input_file.startswith('screenshot') and input_file.endswith('.png'):
        main_idx += 1
        for area_idx, (x, y) in enumerate(areas):
            new_file = 'extracted-{:02d}-{}.png'.format(main_idx, area_idx+1)
            print(new_file)
            subprocess.run([
                '/usr/bin/convert',
                input_file,
                '-crop', '{}x{}+{}+{}'.format(w, h, x, y),
                new_file,
                ])

