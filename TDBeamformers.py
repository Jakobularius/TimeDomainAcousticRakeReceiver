
import numpy as np
from scipy.signal import resample,fftconvolve
from scipy.linalg import toeplitz, inv
import scipy.linalg as la

import pyroomacoustics as pra


'''
We create a new Beamformer class for Rake Perceptually motivated beamformers
'''
class RakeMaxUDR(pra.Beamformer):

    def computeWeights(self, sources, interferers, R_n, delay=0.03, epsilon=5e-3):

        dist_mat = pra.distance(self.R, sources)
        s_time = dist_mat / pra.c
        s_dmp = 1./(4*np.pi*dist_mat)

        dist_mat = pra.distance(self.R, interferers)
        i_time = dist_mat / pra.c
        i_dmp = 1./(4*np.pi*dist_mat)

        # compute offset needed for decay of sinc by epsilon
        offset = np.maximum(s_dmp.max(), i_dmp.max())/(np.pi*self.Fs*epsilon)
        t_min = np.minimum(s_time.min(), i_time.min())
        t_max = np.maximum(s_time.max(), i_time.max())
        

        # adjust timing
        s_time -= t_min - offset
        i_time -= t_min - offset
        Lh = int((t_max - t_min + 2*offset)*float(self.Fs))

        # the channel matrix
        K = sources.shape[1]
        Lg = self.Lg
        off = (Lg - Lh)/2
        L = self.Lg + Lh - 1

        H = np.zeros((Lg*self.M, 2*L))

        for r in np.arange(self.M):

            # build interferer RIR matrix
            hx = pra.lowPassDirac(s_time[r,:,np.newaxis], s_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,:L] = pra.convmtx(hx, Lg).T

            # build interferer RIR matrix
            hq = pra.lowPassDirac(i_time[r,:,np.newaxis], i_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,L:] = pra.convmtx(hq, Lg).T
            
        # Delay of the system in samples
        kappa = int(delay*self.Fs)
        precedence = int(0.030*self.Fs)

        # the constraint
        n = np.minimum(L, kappa+precedence)
        Hnc = H[:,:kappa]
        Hpr = H[:,kappa:n]
        Hc  = H[:,n:L]
        A = np.dot(Hpr, Hpr.T)
        B = np.dot(Hnc, Hnc.T) + np.dot(Hc, Hc.T) + np.dot(H[:,L:], H[:,L:].T) + R_n

        # solve the problem
        SINR, v = la.eigh(A, b=B, eigvals=(self.M*Lg-1, self.M*Lg-1), overwrite_a=True, overwrite_b=True, check_finite=False)
        g_val = np.real(v[:,0])

        # reshape and store
        self.filters = g_val.reshape((self.M, self.Lg))

        import matplotlib.pyplot as plt
        plt.figure()
        plt.subplot(3,1,1)
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,:L].T, g_val))
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,L:].T, g_val))
        plt.legend(('Channel of desired source','Channel of interferer'))
        plt.subplot(3,1,2)
        plt.plot(np.abs(np.fft.rfft(np.dot(H[:,:L].T, g_val))))

        plt.subplot(3,1,3)
        for m in np.arange(self.M):
            plt.plot(np.abs(np.fft.rfft(H[m*self.Lg,:L])))

        # compute and return SNR
        return SINR[0]



'''
We create a new Beamformer class for Rake Perceptually motivated beamformers
'''
class RakePerceptual_TD(pra.Beamformer):

    def computeWeights(self, sources, interferers, R_n, delay=0.03, epsilon=5e-3):

        dist_mat = pra.distance(self.R, sources)
        s_time = dist_mat / pra.c
        s_dmp = 1./(4*np.pi*dist_mat)

        dist_mat = pra.distance(self.R, interferers)
        i_time = dist_mat / pra.c
        i_dmp = 1./(4*np.pi*dist_mat)

        # compute offset needed for decay of sinc by epsilon
        offset = np.maximum(s_dmp.max(), i_dmp.max())/(np.pi*self.Fs*epsilon)
        t_min = np.minimum(s_time.min(), i_time.min())
        t_max = np.maximum(s_time.max(), i_time.max())
        

        # adjust timing
        s_time -= t_min - offset
        i_time -= t_min - offset
        Lh = int((t_max - t_min + 2*offset)*float(self.Fs))

        # the channel matrix
        K = sources.shape[1]
        Lg = self.Lg
        off = (Lg - Lh)/2
        L = self.Lg + Lh - 1

        H = np.zeros((Lg*self.M, 2*L))

        for r in np.arange(self.M):

            # build interferer RIR matrix
            hx = pra.lowPassDirac(s_time[r,:,np.newaxis], s_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,:L] = pra.convmtx(hx, Lg).T

            # build interferer RIR matrix
            hq = pra.lowPassDirac(i_time[r,:,np.newaxis], i_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,L:] = pra.convmtx(hq, Lg).T
            
        # Delay of the system in samples
        kappa = int(delay*self.Fs)

        # the constraint
        A = H[:,:kappa+1]
        b = np.zeros((kappa+1,1))
        b[-1,0] = 1

        # We first assume the sample are uncorrelated
        K_nq = np.dot(H[:,L:], H[:,L:].T) + R_n

        # causal response construction
        C = la.cho_factor(K_nq, overwrite_a=True, check_finite=False)
        B = la.cho_solve(C, A)
        D = np.dot(A.T, B)
        C = la.cho_factor(D, overwrite_a=True, check_finite=False)
        x = la.cho_solve(C, b)
        g_val = np.dot(B, x)

        # reshape and store
        self.filters = g_val.reshape((self.M, self.Lg))

        '''
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,:L].T, g_val))
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,L:].T, g_val))
        plt.legend(('Channel of desired source','Channel of interferer'))
        '''

        # compute and return SNR
        A = np.dot(g_val.T, H[:,:L])
        num = np.dot(A, A.T)
        denom =  np.dot(np.dot(g_val.T, K_nq), g_val)
        return num/denom



'''
We create a new Beamformer class for Rake MaxSINR in time-domain
'''
class RakeMaxSINR_TD(pra.Beamformer):

    def computeWeights(self, sources, interferers, R_n, delay=None, epsilon=5e-3):

        dist_mat = pra.distance(self.R, sources)
        s_time = dist_mat / pra.c
        s_dmp = 1./(4*np.pi*dist_mat)

        dist_mat = pra.distance(self.R, interferers)
        i_time = dist_mat / pra.c
        i_dmp = 1./(4*np.pi*dist_mat)

        # compute offset needed for decay of sinc by epsilon
        offset = np.maximum(s_dmp.max(), i_dmp.max())/(np.pi*self.Fs*epsilon)
        t_min = np.minimum(s_time.min(), i_time.min())
        t_max = np.maximum(s_time.max(), i_time.max())

        # adjust timing
        s_time -= t_min - offset
        i_time -= t_min - offset
        Lh = int((t_max - t_min + 2*offset)*float(self.Fs))

        # the channel matrix
        K = sources.shape[1]
        Lg = self.Lg
        off = (Lg - Lh)/2
        L = self.Lg + Lh - 1

        H = np.zeros((Lg*self.M, 2*L))

        for r in np.arange(self.M):

            # build interferer RIR matrix
            hx = pra.lowPassDirac(s_time[r,:,np.newaxis], s_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,:L] = pra.convmtx(hx, Lg).T

            # build interferer RIR matrix
            hq = pra.lowPassDirac(i_time[r,:,np.newaxis], i_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,L:] = pra.convmtx(hq, Lg).T

        # We first assume the sample are uncorrelated
        K_s = np.dot(H[:,:L], H[:,:L].T)
        K_nq = np.dot(H[:,L:], H[:,L:].T) + R_n

        # Compute TD filters using generalized Rayleigh coefficient maximization
        SINR, v = la.eigh(K_s, b=K_nq, eigvals=(self.M*Lg-1, self.M*Lg-1), overwrite_a=True, overwrite_b=True, check_finite=False)
        g_val = np.real(v[:,0])

        self.filters = g_val.reshape((self.M, Lg))

        '''
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,:L].T, g_val))
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,L:].T, g_val))
        plt.legend(('Channel of desired source','Channel of interferer'))
        '''

        # compute and return SNR
        return SINR[0]


'''
We create a new Beamformer class that minimizes interference and noise with distortionless response
'''
class RakeDistortionless(pra.Beamformer):

    def computeWeights(self, sources, interferers, R_n, delay=0.03, epsilon=5e-3):

        dist_mat = pra.distance(self.R, sources)
        s_time = dist_mat / pra.c
        s_dmp = 1./(4*np.pi*dist_mat)

        dist_mat = pra.distance(self.R, interferers)
        i_time = dist_mat / pra.c
        i_dmp = 1./(4*np.pi*dist_mat)

        # compute offset needed for decay of sinc by epsilon
        offset = np.maximum(s_dmp.max(), i_dmp.max())/(np.pi*self.Fs*epsilon)
        t_min = np.minimum(s_time.min(), i_time.min())
        t_max = np.maximum(s_time.max(), i_time.max())

        # adjust timing
        s_time -= t_min - offset
        i_time -= t_min - offset
        Lh = int((t_max - t_min + 2*offset)*float(self.Fs))

        # the channel matrix
        K = sources.shape[1]
        Lg = self.Lg
        off = (Lg - Lh)/2
        L = self.Lg + Lh - 1

        H = np.zeros((Lg*self.M, 2*L))

        for r in np.arange(self.M):

            # build interferer RIR matrix
            hx = pra.lowPassDirac(s_time[r,:,np.newaxis], s_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,:L] = pra.convmtx(hx, Lg).T

            # build interferer RIR matrix
            hq = pra.lowPassDirac(i_time[r,:,np.newaxis], i_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,L:] = pra.convmtx(hq, Lg).T

        # We first assume the sample are uncorrelated
        K_nq = np.dot(H[:,L:], H[:,L:].T) + R_n

        # constraint
        kappa = int(delay*self.Fs)
        kappa = (Lh+Lg)/2
        A = H[:,:L]
        b = np.zeros((L,1))
        b[kappa,0] = 1

        # filter computation
        C = la.cho_factor(K_nq, overwrite_a=True, check_finite=False)
        B = la.cho_solve(C, A)
        D = np.dot(A.T, B)
        C = la.cho_factor(D, overwrite_a=True, check_finite=False)
        x = la.cho_solve(C, b)
        g_val = np.dot(B, x)

        # reshape and store
        self.filters = g_val.reshape((self.M, self.Lg))

        '''
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,:L].T, g_val))
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,L:].T, g_val))
        plt.legend(('Channel of desired source','Channel of interferer'))
        '''

        # compute and return SNR
        A = np.dot(g_val.T, H[:,:L])
        num = np.dot(A, A.T)
        denom =  np.dot(np.dot(g_val.T, K_nq), g_val)

        return num/denom


'''
We create a new Beamformer class for Rake One-Forcing in time-domain
'''
class RakeOF_TD(pra.Beamformer):

    def computeWeights(self, sources, interferers, R_n, epsilon=5e-3):

        dist_mat = pra.distance(self.R, sources)
        s_time = dist_mat / pra.c
        s_dmp = 1./(4*np.pi*dist_mat)

        dist_mat = pra.distance(self.R, interferers)
        i_time = dist_mat / pra.c
        i_dmp = 1./(4*np.pi*dist_mat)

        # compute offset needed for decay of sinc by epsilon
        offset = np.maximum(s_dmp.max(), i_dmp.max())/(np.pi*self.Fs*epsilon)
        t_min = np.minimum(s_time.min(), i_time.min())
        t_max = np.maximum(s_time.max(), i_time.max())

        # adjust timing
        s_time -= t_min - offset
        i_time -= t_min - offset
        Lh = np.ceil((t_max - t_min + 2*offset)*float(self.Fs))

        # the channel matrix
        K = sources.shape[1]
        Lg = self.Lg
        off = (Lg - Lh)/2
        L = self.Lg + Lh - 1

        H = np.zeros((Lg*self.M, 2*L))
        As = np.zeros((Lg*self.M, K))

        for r in np.arange(self.M):

            # build constraint matrix
            hs = pra.lowPassDirac(s_time[r,:,np.newaxis], s_dmp[r,:,np.newaxis], self.Fs, Lh)[:,::-1]
            As[r*Lg+off:r*Lg+Lh+off,:] = hs.T

            # build interferer RIR matrix
            hx = pra.lowPassDirac(s_time[r,:,np.newaxis], s_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,:L] = pra.convmtx(hx, Lg).T

            # build interferer RIR matrix
            hq = pra.lowPassDirac(i_time[r,:,np.newaxis], i_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            H[r*Lg:(r+1)*Lg,L:] = pra.convmtx(hq, Lg).T

        ones = np.ones((K,1))

        # We first assume the sample are uncorrelated
        K_x = np.dot(H[:,:L], H[:,:L].T)
        K_nq = np.dot(H[:,L:], H[:,L:].T) + R_n

        # Compute the TD filters
        K_nq_inv = np.linalg.inv(K_x+K_nq)
        C = np.dot(K_nq_inv, As)
        B = np.linalg.inv(np.dot(As.T, C))
        g_val = np.dot(C, np.dot(B, ones))
        self.filters = g_val.reshape((self.M,Lg))

        import matplotlib.pyplot as plt
        plt.figure()
        plt.subplot(3,1,1)
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,:L].T, g_val))
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,L:].T, g_val))
        plt.legend(('Channel of desired source','Channel of interferer'))
        plt.subplot(3,1,2)
        for m in np.arange(self.M):
            plt.plot(np.arange(Lh)/float(self.Fs), H[m*Lg,:Lh])
        plt.subplot(3,1,3)
        for m in np.arange(self.M):
            plt.plot(np.arange(Lh)/float(self.Fs), H[m*Lg,L:L+Lh])

        # compute and return SNR
        A = np.dot(g_val.T, H[:,:L])
        num = np.dot(A, A.T)
        denom =  np.dot(np.dot(g_val.T, K_nq), g_val)

        return num/denom


'''
We create a new Beamformer class for Rake MVDR in time-domain
'''
class RakeMVDR_TD(pra.Beamformer):

    def computeWeights(self, sources, interferers, R_n, delay=0.03, epsilon=5e-3):

        dist_mat = pra.distance(self.R, sources)
        s_time = dist_mat / pra.c
        s_dmp = 1./(4*np.pi*dist_mat)

        dist_mat = pra.distance(self.R, interferers)
        i_time = dist_mat / pra.c
        i_dmp = 1./(4*np.pi*dist_mat)

        offset = np.maximum(s_dmp.max(), i_dmp.max())/(np.pi*self.Fs*epsilon)
        t_min = np.minimum(s_time.min(), i_time.min())
        t_max = np.maximum(s_time.max(), i_time.max())

        s_time -= t_min - offset
        i_time -= t_min - offset
        Lh = int((t_max - t_min + 2*offset)*float(self.Fs))

        if ((Lh-1) > (self.M-1)*self.Lg):
            import warnings
            wng = "Beamforming filters length (%d) are shorter than minimum required (%d)." % (self.Lg, Lh)
            warnings.warn(wng, UserWarning)

        # the channel matrix
        Lg = self.Lg
        L = self.Lg + Lh - 1
        H = np.zeros((Lg*self.M, 2*L))

        for r in np.arange(self.M):

            hs = pra.lowPassDirac(s_time[r,:,np.newaxis], s_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            row = np.pad(hs, ((0,L-len(hs))), mode='constant')
            col = np.pad(hs[:1], ((0, Lg-1)), mode='constant')
            H[r*Lg:(r+1)*Lg,0:L] = toeplitz(col, row)

            hi = pra.lowPassDirac(i_time[r,:,np.newaxis], i_dmp[r,:,np.newaxis], self.Fs, Lh).sum(axis=0)
            row = np.pad(hi, ((0,L-len(hi))), mode='constant')
            col = np.pad(hi[:1], ((0, Lg-1)), mode='constant')
            H[r*Lg:(r+1)*Lg,L:2*L] = toeplitz(col, row)

        # the constraint vector
        kappa = int(delay*self.Fs)
        #kappa = np.minimum(int(0.6*(Lh+Lg)), int(2*t_max*self.Fs))
        h = H[:,kappa]

        # We first assume the sample are uncorrelated
        R_xx = np.dot(H[:,:L], H[:,:L].T)
        K_nq = np.dot(H[:,L:], H[:,L:].T) + R_n

        # Compute the TD filters
        C = la.cho_factor(R_xx + K_nq, check_finite=False)
        g_val = la.cho_solve(C, h)

        g_val /= np.inner(h, g_val)
        self.filters = g_val.reshape((self.M,Lg))


        '''
        import matplotlib.pyplot as plt
        plt.figure()
        plt.subplot(2,1,1)
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,:L].T, g_val))
        plt.plot(np.arange(L)/float(self.Fs), np.dot(H[:,L:].T, g_val))
        plt.legend(('Channel of desired source','Channel of interferer'))
        plt.subplot(2,1,2)
        for m in np.arange(self.M):
            plt.plot(np.arange(Lh)/float(self.Fs), H[m*Lg,:Lh])
        '''

        # compute and return SNR
        num = np.inner(g_val.T, np.dot(R_xx, g_val))
        denom =  np.inner(np.dot(g_val.T, K_nq), g_val)

        return num/denom

