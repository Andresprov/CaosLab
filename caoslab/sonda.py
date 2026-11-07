class SondaHTTP:
    def __init__(self, url, peticiones_por_segundo, timeout_s):
        pass

    def iniciar(self):
        raise NotImplementedError

    def recoger(self):
        raise NotImplementedError

    def detener(self):
        raise NotImplementedError
