import logging

NAME = "walkman"
"""Software name"""

# WARNINGS and LOGGINGS should be caught by the same handlers.
logging.captureWarnings(True)

LOGGER = logging.getLogger("py.warnings")
"""Global logger"""

LOGGER.addHandler(logging.StreamHandler())
LOGGER.addHandler(logging.FileHandler("./.walkman.log"))
LOGGER.setLevel(logging.INFO)

MODULE_PACKAGE_NAME = "walkman_modules"

EMPTY_MODULE_INSTANCE_NAME = "empty.empty"

ICON = b"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CiAgICB4bWxuczp0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29tL3RpZmYvMS4wLyIKICAgIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIKICAgeG1wTU06RG9jdW1lbnRJRD0iZ2ltcDpkb2NpZDpnaW1wOmViYjQ4YTMyLTg2MGEtNDI5OS04YzJmLTVmOTFlZDc2MjAxNSIKICAgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDo2Nzc4MGE1MC03ZTUwLTQ5ZjAtOGUzNi03NWFlMTZlOTIxZWQiCiAgIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDplN2M2ODM4MS05NzI5LTQ2Y2UtOTJlYy1kYTQ2NzRiMTNjZWYiCiAgIEdJTVA6QVBJPSIyLjAiCiAgIEdJTVA6UGxhdGZvcm09IkxpbnV4IgogICBHSU1QOlRpbWVTdGFtcD0iMTY1NDcyNDc2NjMzNTc3OCIKICAgR0lNUDpWZXJzaW9uPSIyLjEwLjIyIgogICBkYzpGb3JtYXQ9ImltYWdlL3BuZyIKICAgdGlmZjpPcmllbnRhdGlvbj0iMSIKICAgeG1wOkNyZWF0b3JUb29sPSJHSU1QIDIuMTAiPgogICA8aXB0Y0V4dDpMb2NhdGlvbkNyZWF0ZWQ+CiAgICA8cmRmOkJhZy8+CiAgIDwvaXB0Y0V4dDpMb2NhdGlvbkNyZWF0ZWQ+CiAgIDxpcHRjRXh0OkxvY2F0aW9uU2hvd24+CiAgICA8cmRmOkJhZy8+CiAgIDwvaXB0Y0V4dDpMb2NhdGlvblNob3duPgogICA8aXB0Y0V4dDpBcnR3b3JrT3JPYmplY3Q+CiAgICA8cmRmOkJhZy8+CiAgIDwvaXB0Y0V4dDpBcnR3b3JrT3JPYmplY3Q+CiAgIDxpcHRjRXh0OlJlZ2lzdHJ5SWQ+CiAgICA8cmRmOkJhZy8+CiAgIDwvaXB0Y0V4dDpSZWdpc3RyeUlkPgogICA8eG1wTU06SGlzdG9yeT4KICAgIDxyZGY6U2VxPgogICAgIDxyZGY6bGkKICAgICAgc3RFdnQ6YWN0aW9uPSJzYXZlZCIKICAgICAgc3RFdnQ6Y2hhbmdlZD0iLyIKICAgICAgc3RFdnQ6aW5zdGFuY2VJRD0ieG1wLmlpZDpiNjQyOGE2OS1iYTg1LTQ2N2UtOWI2Zi0wYTAyYTIwZjk4NzEiCiAgICAgIHN0RXZ0OnNvZnR3YXJlQWdlbnQ9IkdpbXAgMi4xMCAoTGludXgpIgogICAgICBzdEV2dDp3aGVuPSIrMDI6MDAiLz4KICAgICA8cmRmOmxpCiAgICAgIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiCiAgICAgIHN0RXZ0OmNoYW5nZWQ9Ii8iCiAgICAgIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6NGZhODA1MzItYzE0My00NGRlLWI3Y2EtY2U2MGM3MTM4MGEyIgogICAgICBzdEV2dDpzb2Z0d2FyZUFnZW50PSJHaW1wIDIuMTAgKExpbnV4KSIKICAgICAgc3RFdnQ6d2hlbj0iKzAyOjAwIi8+CiAgICA8L3JkZjpTZXE+CiAgIDwveG1wTU06SGlzdG9yeT4KICAgPHBsdXM6SW1hZ2VTdXBwbGllcj4KICAgIDxyZGY6U2VxLz4KICAgPC9wbHVzOkltYWdlU3VwcGxpZXI+CiAgIDxwbHVzOkltYWdlQ3JlYXRvcj4KICAgIDxyZGY6U2VxLz4KICAgPC9wbHVzOkltYWdlQ3JlYXRvcj4KICAgPHBsdXM6Q29weXJpZ2h0T3duZXI+CiAgICA8cmRmOlNlcS8+CiAgIDwvcGx1czpDb3B5cmlnaHRPd25lcj4KICAgPHBsdXM6TGljZW5zb3I+CiAgICA8cmRmOlNlcS8+CiAgIDwvcGx1czpMaWNlbnNvcj4KICA8L3JkZjpEZXNjcmlwdGlvbj4KIDwvcmRmOlJERj4KPC94OnhtcG1ldGE+CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAKPD94cGFja2V0IGVuZD0idyI/PsyYfdsAAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElNRQfmBggVLga+tELyAAAAYnRFWHRDb21tZW50AEZpbGUgc291cmNlOiBodHRwOi8vY29tbW9ucy53aWtpbWVkaWEub3JnL3dpa2kvRmlsZTpTb255X1RDRC1EMTAwX0RBVC1SZWNvcmRlcl9XYWxrbWFuLmpwZ5zOFFEAAAgkSURBVFjD7VhJr+VGGf2mqrLLvrbf/Hp6PUURLSKiEIUIhAQSG5QVC34GrBASa34bk9QoNBF00nN3utNvHu7ka1+76mNx+0UoJKD3OlJY5MiSLXvho1Pn+07Vh6oK3zQI/g/wLYlTyJe+PT4+PD46ZGERIywsbMSKiLGGRZgIAAHw6yKB/2nMGMPvfvOrj+/82TkrxhbVap7nIfZp6qOGvu+zLPd57tMszbLUZ94XRVl6761NxZi1tY3LV669rhInJ8c7L5+2szkDGbFhPvF+NUnTGEOe+yRJ+9DN6vpg+0kEJFRAYmYkQaIQojHu17/9fVksvZYnDg72rHWqgIRlVV3aug4ETdv0fX8yHO/tHR4fDdu2E5chWiZhZkREVCJMnAOIj+5/8rpKDIfDEFQjEOC8nR0f7917PkQRBCAkVQ19F2Jk1ctr2dblC0xMiErIREw4GjW3//LHd959H5HOT4KRAFABEDFGNUZ8nikzMRNiVI0haIhd0ypS3TZlUpICMhESEWd5enS4f3iwv7q28RoliuR8RsyqoCEwUuoMAihgHyMQkQgyGWf7SPW0ESQUZhJhIaI0cRq7j+9+9FqeYBZjnM+8gkYADZpZ7lW7vlOAvu9DjEDknOuBoyoACBITACESMnMI7Ye3/zCft+cnMRgUqpgPKlAE1RBC6sggGWEiFBFmThY3Y8XYtplpN+nbUWxHGhsiSlI/Ho5ePH96fhJFUYiYJPOqqoBdCN7aycm4GU/7WdtOaonRMjnD1nCMOK4bZCMmIXGMhphSZ4Hwozt/BdBzGrMoCzaWiBVBQWOMPjU/fHur74IIR419iM5aAEAkw7S9f9Sq04CEhAqFIxIqB/7Rg3+cnBxX1fJ5lLDWXbh4MUYNfcQIMYR5FwnZZ4UYBygiToEQhcQqmkGe52laDfKqyKsiZ2FmttYkVh4//OT8AXbj+g3jHCApqCpMRkMkEgmD3JWF39jcmLfd6vrK+vqKWFtVlThLTMTEzMxMRESoCn+7/afQ9+cksb6x4dIs8ZkqAiISN82sC7ZuNEQzmdSpz2ezfngynbfzWdMJCy8aySsGxEzW2v3d3d3d7XOmaFlVIjYvink9WgRmURRF6UMIoAAI1lqCXqykKbm06rqYWABEIsJTAIR8kD+4f/fipSvnUaIsKyRJfQ6ACMjM02k9m0xDF0A5BBiNRnXddX2cdzAZneztbrMIn+JV/RpTFP7e3TtNMzuPEoNBgczGJaqIiMgMAAF5aWk5hKiqPstC3zOTAtazuqoGInIqAHz+0HUdxPbpk/vfufX2mZUYDAYucSFCXBQiMbEw0cHeHqEaISZ6eP+B90lZZBc3V4ejsZwqYUREWERExFpjrfnn32//9+30l5MQkSuXrwAhABEyMiFSVJ3P5xD62M+NYUXs5m3f99YmGiMiyqIymIzI4rLWWmtPjnaPjvbPs8fc2tqyNrFJQiSoBAiqymIQUYxhprKqJpPae4+Ia6vLMaqzzlpnxAiLMWKtcc4lSeKc+fTJwzN7AgA21jfZmLwoFILPlzY2NtfW14cnB/V0FNuWqMuyou3o6GgWQRXdZy/2uq4RNssrm9euX0FoVFVVEVFjvHf3w++98wNmORuJsqoA2WeDn3/wwfWbb54cHh7s7+R5lqYpERGBgsbQh34OCDEERIhRmSVJcpV8Mhp71/ZdS0QaYzeZ7O68vHhp62wkirIUZnTJvY/v7O8+XpgOAI8PO2IGgKbtjDHOcpIkqhBC33VdWVTTcEQ0XFu5urO9UxQWEVW168PzZw+/isRXeqIsS+ssC0/GEwCIMcYYhyfHs+Ehz2eh74vc+9Qi4qI/Hh8eIMbpdKwKMfSHB4/qWT0e1afOcC+efNLN52cjYa29sHkhKkwnUzxthdNpnTMnqFWRRI2ImCQJIjJzUa1c3bqc5amqAiABGW4ePHiSpkmSJD5NE8c728/PfAK7evX6aDRpux5xEQe8srqC5Uq+ttorOedE5PM+XRTZy5cHGnERYMjkfbK7s22tdc6maZJ6v/3i8dk8sYixi5cuDQ+2EXHxv8FgEBX2R41L3L/HxAL5IH/VLwGIUCkOBt4aAwAIoFGP9p83TZ0k/gwkyqr03o/FxAinAU0A4KxBRAREerVMi0+IiApEhAhIeHQ4/O5btxjJiREkROh7v7+7feXqzTMsR5blRGJtMqvbL4QTEwmRRKA+UBdwOoVpHcYTQmBhMQIA48nw1q03F+soIlnql5ZWxie7Z/PEYDDo5p1NkvF4QkSLSOCu51mL8w77HpkAMIC2zOR9slSJtSKMiJPx+EfvvyciRLDQSVVj30XFs3kiy7JmPncumU5OmJmFiZgGRkERMYbYtp111hClzM4ZY4wIM5EqFHk+Go+HL0bD0XgyrseTadN2axe2fvHLn56NBCK+8cYbL58/s9aXS+vdfLrIRhbDRIQUFULXNc2sruujo5OmadtZUzdNPWu6ef9qsmAcI0awb73z7o9/8jNr3dlIAMCNGzc/ffJoNDp88OBF7tO2rfuu6+Zd08xmTeNsUjdTZx2zsAggIBBQkufpqzplEZEky9/+/ntXr938qtPp/yCxur5OhMsrm8Pjg8mIAQkRCZFtktmEEK1PQYGYEJGRFDCq+izf2LywtLxclkvV8sqgKAjxPCm6wPLyMotZW1vd39357LOdoIqI169fE5IIqohVtbS0tFKUlffe+ywvisFgkCTJ605qvoBnz54+ffxkWk8QKc/zsiwHRZH5zGfe+2zROb7+cdG3I8RvSXzz+BdrSZtPmv+3UgAAAABJRU5ErkJggg=="
