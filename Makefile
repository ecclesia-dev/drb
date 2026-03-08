PREFIX = /usr/local

COMMENTARY = commentary/haydock.tsv commentary/lapide.tsv commentary/douai-1609.tsv \
             commentary/aquinas-catena.tsv commentary/aquinas-epistles.tsv \
             commentary/aquinas-job.tsv commentary/aquinas-psalms.tsv \
             commentary/aquinas-isaiah.tsv commentary/chrysostom-matthew.tsv \
             commentary/chrysostom-john.tsv commentary/chrysostom-epistles.tsv

drb: drb.sh drb.awk drb.tsv drb-1609.tsv $(COMMENTARY)
	cat drb.sh > $@
	echo 'exit 0' >> $@
	echo '#EOF' >> $@
	tar czf - drb.awk drb.tsv drb-1609.tsv $(COMMENTARY) >> $@
	chmod +x $@

test: drb.sh
	shellcheck -s sh drb.sh

clean:
	rm -f drb

install: drb
	mkdir -p $(DESTDIR)$(PREFIX)/bin
	cp -f drb $(DESTDIR)$(PREFIX)/bin
	chmod 755 $(DESTDIR)$(PREFIX)/bin/drb
	mkdir -p $(DESTDIR)$(PREFIX)/share/bash-completion/completions
	cp -f completion.bash $(DESTDIR)$(PREFIX)/share/bash-completion/completions/drb

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/drb
	rm -f $(DESTDIR)$(PREFIX)/share/bash-completion/completions/drb

hooks:
	sh scripts/install-hooks.sh

.PHONY: test clean install uninstall hooks
