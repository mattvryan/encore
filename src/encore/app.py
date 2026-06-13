import rumps


class EncoreApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("Encore", quit_button=None)
        self.menu = ["Sync Now", None, "Quit"]

    @rumps.clicked("Sync Now")
    def sync_now(self, _) -> None:
        rumps.notification("Encore", "", "Sync not yet implemented")

    @rumps.clicked("Quit")
    def quit_app(self, _) -> None:
        rumps.quit_application()
