<?php

namespace App\Exceptions;

use RuntimeException;

/*
 * Kegagalan yang berasal dari engine analisis Python.
 *
 * Dibedakan dari RuntimeException biasa supaya lapisan HTTP bisa mengubahnya
 * menjadi 422 dengan pesan yang sudah dapat dibaca pengguna, alih-alih 500 yang
 * menyembunyikan penyebabnya.
 */
class PythonEngineException extends RuntimeException
{
}
