from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_mysqldb import MySQL
from config import Config
import MySQLdb.cursors

app = Flask(__name__)
app.config.from_object(Config)
mysql = MySQL(app)

# Route pour la page d'accueil
@app.route('/')
def index():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM spectacles')
    spectacles = cursor.fetchall()
    return render_template('index.html', spectacles=spectacles)


# Route pour s'enregistrer
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']
        confirm_password = request.form['confirm_password']
        role = request.form['role']  # Récupérer le rôle sélectionné (client ou admin)

        if mot_de_passe != confirm_password:
            message = "Les mots de passe ne correspondent pas."
            return render_template('register.html', message=message)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM utilisateurs WHERE email = %s', (email,))
        compte = cursor.fetchone()

        if compte:
            message = 'Un compte avec cet email existe déjà.'
        else:
            # Insérer l'utilisateur avec le rôle choisi
            cursor.execute('INSERT INTO utilisateurs (nom, email, mot_de_passe, role) VALUES (%s, %s, %s, %s)',
                           (nom, email, mot_de_passe, role))
            mysql.connection.commit()
            message = 'Enregistrement réussi. Vous pouvez maintenant vous connecter.'
            return redirect(url_for('login'))

        return render_template('register.html', message=message)
    return render_template('register.html')



# Route pour s'authentifier
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM utilisateurs WHERE email = %s AND mot_de_passe = %s', (email, mot_de_passe))
        utilisateur = cursor.fetchone()

        if utilisateur:
            # Enregistrement de la session de l'utilisateur
            session['loggedin'] = True
            session['id'] = utilisateur['id']
            session['nom'] = utilisateur['nom']
            session['role'] = utilisateur['role']

            # Redirection en fonction du rôle
            if utilisateur['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            message = 'Email ou mot de passe incorrect.'
    
    return render_template('login.html', message=message)


# Route pour ajouter un spectacle (admin)
@app.route('/admin/add_spectacle', methods=['GET', 'POST'])
def add_spectacle():
    if session.get('loggedin') and session.get('role') == 'admin':
        # Seul un administrateur peut accéder à cette page
        if request.method == 'POST':
            titre = request.form['titre']
            date_spectacle = request.form['date_spectacle']
            description = request.form['description']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO spectacles (titre, date_spectacle, description) VALUES (%s, %s, %s)',
                           (titre, date_spectacle, description))
            mysql.connection.commit()

            return redirect(url_for('index'))
        return render_template('add_spectacle.html')
    else:
        return redirect(url_for('login'))



# Route pour réserver un spectacle (client)
@app.route('/reserve/<int:spectacle_id>', methods=['POST'])
def reserve(spectacle_id):
    if session.get('loggedin') and session.get('role') == 'client':
        places_reservees = request.form['places']
        utilisateur_id = session['id']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Vérifier si la réservation existe déjà
        cursor.execute('SELECT * FROM reservations WHERE utilisateur_id = %s AND spectacle_id = %s', (utilisateur_id, spectacle_id))
        reservation = cursor.fetchone()

        if reservation:
            message = "Vous avez déjà réservé pour ce spectacle."
            return redirect(url_for('dashboard', message=message))
        
        # Ajouter une nouvelle réservation
        cursor.execute('INSERT INTO reservations (utilisateur_id, spectacle_id, places_reservees) VALUES (%s, %s, %s)', 
                       (utilisateur_id, spectacle_id, places_reservees))
        mysql.connection.commit()
        
        message = "Réservation effectuée avec succès."
        return redirect(url_for('dashboard', message=message))
    else:
        return redirect(url_for('login'))

# Route pour dashboard (client)
@app.route('/dashboard')
def dashboard():
    if session.get('loggedin') and session.get('role') == 'client':
        utilisateur_id = session['id']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT s.titre, s.date_spectacle, r.places_reservees FROM reservations r JOIN spectacles s ON r.spectacle_id = s.id WHERE r.utilisateur_id = %s', (utilisateur_id,))
        reservations = cursor.fetchall()

        return render_template('dashboard.html', reservations=reservations)
    else:
        return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('loggedin') and session.get('role') == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Requête SQL pour obtenir les spectacles et le nombre de réservations
        cursor.execute('''
            SELECT s.id, s.titre, s.date_spectacle, s.description, COUNT(r.id) AS nombre_reservations
            FROM spectacles s
            LEFT JOIN reservations r ON s.id = r.spectacle_id
            GROUP BY s.id, s.titre, s.date_spectacle, s.description
        ''')
        spectacles = cursor.fetchall()

        return render_template('admin_dashboard.html', spectacles=spectacles)
    else:
        return redirect(url_for('login'))





@app.route('/logout')
def logout():
    session.clear()  # Efface toutes les données de session
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
