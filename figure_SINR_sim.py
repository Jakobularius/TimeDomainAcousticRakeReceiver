
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from scipy.linalg import toeplitz
from scipy.io import wavfile
from scipy.signal import resample,fftconvolve

import pyroomacoustics as pra
import TDBeamformers as tdb

# simulation parameters
bf_names = ('Rake-MaxSINR', 'Rake-Perceptual', 'Rake-MVDR')
bf_designs = (tdb.RakeMaxSINR_TD, tdb.RakePerceptual_TD, tdb.RakeMVDR_TD)
max_source = 10
loops = 10000
SINR = np.zeros((max_source, len(bf_designs), loops))

# Beam pattern figure properties
freq=[800, 1600]
figsize=(1.88,2.24)
xlim=[-4,8]
ylim=[-4.9,9.4]

# Some simulation parameters
Fs = 8000
t0 = 1./(Fs*np.pi*1e-2)  # starting time function of sinc decay in RIR response
absorption = 0.90
max_order_sim = 3
sigma2_n = 1e-15
SNRdB = 10.

# Room 1 : Shoe box
room_dim = np.array([4, 6])

# the good source is fixed for all 
good_source = [1, 4.5]       # good source
normal_interferer = [2.8, 4.3]   # interferer
hard_interferer = [1.5, 3]   # interferer in direct path
#normal_interferer = hard_interferer

# microphone array design parameters
mic1 = [2, 1.5]         # position
M = 8                    # number of microphones
d = 0.08                # distance between microphones
phi = 0.                # angle from horizontal
max_order_design = 1    # maximum image generation used in design
shape = 'Linear'        # array shape
Lg_t = 0.03             # Filter size in seconds
Lg = np.ceil(Lg_t*Fs)   # Filter size in samples
delay = 0.02            # delay of beamformer

# define the FFT length
N = 1024

# create a microphone array
if shape is 'Circular':
    R = pra.circular2DArray(mic1, M, phi, d*M/(2*np.pi)) 
else:
    R = pra.linear2DArray(mic1, M, phi, d) 
center = R.mean(axis=1, keepdims=True)

# create the room with sources and mics
room1 = pra.Room.shoeBox2D(
    [0,0],
    room_dim,
    Fs,
    t0 = t0,
    max_order=max_order_sim,
    absorption=absorption,
    sigma2_awgn=sigma2_n)

for i in np.arange(max_source):
    for n in np.arange(loops):

        # Add new source and interferer to the room
        source = np.random.random(2)*room_dim
        room1.addSource(source)

        interferer = np.random.random(2)*room_dim
        room1.addSource(interferer)

        # compute noise power for 20dB SNR
        dc = np.sqrt(((source[:,np.newaxis] - center)**2).sum())
        sigma2_n = 10.**(-SNRdB/10.)/(4.*np.pi*dc)**2

        # Select their nearest image sources (from the array center)
        good_sources = room1.sources[0].getImages(n_nearest=i+1, ref_point=center)
        bad_sources = room1.sources[1].getImages(n_nearest=1, ref_point=center)

        # compute SNR for all three beamformers
        for t in np.arange(len(bf_designs)):
            mics = bf_designs[t](R, Fs, N, Lg=Lg)
            SINR[i,t,n] = mics.computeWeights(good_sources, bad_sources, sigma2_n*np.eye(mics.Lg*mics.M), delay=delay)

        # remove the source and interferer from the room
        room1.sources.pop()
        room1.sources.pop()

    print 'Finished %d sources.' % (i)

np.save('data/SINR_data.npy', SINR)
