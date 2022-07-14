def setup():
    from .qt.viewer import SmallMultiplesViewer # noqa
    from glue.config import qt_client
    qt_client.add(SmallMultiplesViewer)