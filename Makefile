PREFIX = /usr/local

drb: drb.sh drb.awk drb.tsv drb-1609.tsv haydock.tsv lapide.tsv douai-1609.tsv aquinas-catena.tsv aquinas-epistles.tsv aquinas-job.tsv aquinas-psalms.tsv aquinas-isaiah.tsv chrysostom-matthew.tsv chrysostom-john.tsv chrysostom-epistles.tsv vulgate-normalized.tsv
	cat drb.sh > $@
	echo 'exit 0' >> $@
	echo '#EOF' >> $@
	tar czf - drb.awk drb.tsv drb-1609.tsv haydock.tsv lapide.tsv douai-1609.tsv aquinas-catena.tsv aquinas-epistles.tsv aquinas-job.tsv aquinas-psalms.tsv aquinas-isaiah.tsv chrysostom-matthew.tsv chrysostom-john.tsv chrysostom-epistles.tsv vulgate-normalized.tsv >> $@
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
