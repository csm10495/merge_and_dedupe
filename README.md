# merge_and_dedupe.py

This is a script to help merge/dedup a whole bunch of xml files from SMS Backup & Restore: https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore&hl=en_US&gl=US

It should work with Python 3.10 or more recent.

```
python merge_and_dedupe.py -i <DIRECTORY_WITH_INPUT_XMLS> -o <OUTPUT_DIR>
```

After running this, in theory you can restore the new file to your device and move on.

Note: I'm not affiliated with the company that makes this app.. just an engineer who was annoyed at all the files it can make.
Also: Please check the outputs, and be sure they're correct looking before deleting old inputs.

## License

MIT License - 2024 - Charles Machalow