from collections import OrderedDict
import logging
import os
import shutil
import subprocess

import simtk.unit as units

from intermol.desmond.desmond_parser import load, save


DES_PATH = ''
logger = logging.getLogger('InterMolLog')


to_canonical = {
    'stretch': 'bond',

    'angle': 'angle',

    'dihedral': 'dihedral',

    'pair_vdw': 'vdw-14',
    'nonbonded_vdw': ['vdw', 'dispersive'],

    'pair_elec': 'coulomb-14',

    'E_p': 'potential'
}


def get_desmond_energy_from_file(energy_file):
    """Parses the desmond energy file. """
    with open(energy_file, 'r') as f:
        data = []
        types = []

        # First line of enegrp.dat file contains total energy terms.
        line = f.readline()
        # Just to make sure the line is what we think it is.
        if line.startswith('time=0.000000'):
            terms = line.split()
            terms = terms[1:-2]  # Exclude time, pressure, and volume.
            for term in terms:
                key, value = term.split('=')
                types.append(key)
                data.append(float(value))

        # Parse rest of file for individual energy groups.
        for line in f:
            if '(0.000000)' in line:  # Time = 0.0
                words = line.split()
                if words[-1] == 'total':
                    continue
                key = words[0]
                if key:
                    types.append(key)
                    data.append(words[-1])
    data = [float(value) * units.kilocalories_per_mole for value in data]
    e_out = OrderedDict(zip(types, data))

    return e_out


def energies(cms, cfg, des_path):
    """Evalutes energies of DESMOND files

    Args:
        cms (str): Path to .cms file.
        cfg (str): Path to .cfg file.
        des_path (str): Path to DESMOND binaries.
    Returns:
        tot_energy:
        energy_file:

    """
    logger.info('Evaluating energy of {0}'.format(cms))

    cms = os.path.abspath(cms)
    cfg = os.path.abspath(cfg)
    direc, cms_filename = os.path.split(cms)
    cwd = os.getcwd()
    name = os.path.splitext(cms_filename)[0]
    energy_file = '%s/%s.enegrp.dat' % (direc, name)
    if des_path and not (des_path == ''):
        desmond_bin = os.path.join(des_path,'desmond')
    elif os.environ.get('SCHRODINGER'):
        desmond_bin = os.path.join(os.environ.get('SCHRODINGER'), 'desmond')
    else:
        raise Exception('Desmond binary not found')

    # Use DESMOND To evaluate energy
    #    cd to directory of cms file so that files generated by desmond
    #    don't clog the working directory
    os.chdir(direc)
    if os.path.exists('trj'):
        shutil.rmtree('trj')
    cmd = [desmond_bin, '-WAIT', '-P', '1', '-in', cms, '-JOBNAME', name, '-c', cfg]
    logger.debug('Running DESMOND with command:\n    %s' % ' '.join(cmd))
    with open('desmond_stdout.txt', 'w') as out, open('desmond_stderr.txt', 'w') as err:
        exit = subprocess.call(cmd, stdout=out, stderr=err)

    if exit:
        logger.error('Energy evaluation failed. See %s/desmond_stderr.txt' % direc)
        os.chdir(cwd) # return directory up a level again
        raise Exception('Energy evaluation failed for {0}'.format(cms))

    tot_energy = get_desmond_energy_from_file(energy_file)
    # for now, remove the desmond '-out.cms' file.
    outcms = cms[:-4] + '-out' + cms[-4:]
    os.remove(outcms)
    os.chdir(cwd) # return directory up a level again
    return tot_energy, energy_file
